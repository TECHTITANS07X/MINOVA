import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../models/shift_entry.dart';

class ApiService {
  static const String baseUrl = 'http://localhost:8000/api/v1';
  static final _storage = FlutterSecureStorage();

  static Future<String?> _getToken() async {
    return await _storage.read(key: 'access_token');
  }

  static Future<Map<String, String>> _headers() async {
    final token = await _getToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  static Future<Map<String, dynamic>> login(String username, String password) async {
    final resp = await http.post(
      Uri.parse('$baseUrl/auth/token'),
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: {'username': username, 'password': password, 'grant_type': 'password'},
    );
    if (resp.statusCode == 200) {
      final data = jsonDecode(resp.body);
      await _storage.write(key: 'access_token', value: data['access_token']);
      await _storage.write(key: 'refresh_token', value: data['refresh_token']);
      return data;
    }
    throw Exception('Login failed: ${resp.statusCode}');
  }

  static Future<List<Mine>> fetchMines() async {
    final resp = await http.get(Uri.parse('$baseUrl/admin/mines'), headers: await _headers());
    if (resp.statusCode == 200) {
      final list = jsonDecode(resp.body) as List;
      return list.map((j) => Mine.fromJson(j)).toList();
    }
    return [];
  }

  static Future<Map<String, dynamic>> pushBatch(List<ShiftEntry> entries, String deviceId) async {
    final resp = await http.post(
      Uri.parse('$baseUrl/sync/push'),
      headers: await _headers(),
      body: jsonEncode({
        'device_id': deviceId,
        'entries': entries.map((e) => e.toJson()).toList(),
        'client_timestamp': DateTime.now().toUtc().toIso8601String(),
      }),
    );
    return jsonDecode(resp.body);
  }

  static Future<Map<String, dynamic>> pullDelta(String mineId, String? cursor) async {
    final params = {'mine_id': mineId, if (cursor != null) 'cursor': cursor};
    final uri = Uri.parse('$baseUrl/sync/pull').replace(queryParameters: params);
    final resp = await http.get(uri, headers: await _headers());
    return jsonDecode(resp.body);
  }

  static Future<void> submitEntry(ShiftEntry entry) async {
    await http.post(
      Uri.parse('$baseUrl/entries/'),
      headers: await _headers(),
      body: jsonEncode(entry.toJson()),
    );
  }
}
