import 'dart:convert';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import 'package:path_provider/path_provider.dart';
import '../models/shift_entry.dart';

class LocalDb {
  static Database? _db;

  static Future<Database> get database async {
    if (_db != null) return _db!;
    _db = await _initDb();
    return _db!;
  }

  static Future<Database> _initDb() async {
    final dir = await getApplicationDocumentsDirectory();
    final path = join(dir.path, 'minova.db');
    return openDatabase(
      path,
      version: 1,
      onCreate: (db, version) async {
        await db.execute('''
          CREATE TABLE shift_entries (
            id TEXT PRIMARY KEY,
            mine_id TEXT NOT NULL,
            shift_date TEXT NOT NULL,
            shift_number INTEGER NOT NULL,
            status TEXT DEFAULT 'draft',
            submitted_by TEXT,
            submitted_at TEXT,
            values_json TEXT,
            remarks TEXT,
            is_synced INTEGER DEFAULT 0,
            updated_at TEXT NOT NULL
          )
        ''');
        await db.execute('''
          CREATE TABLE sync_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id TEXT NOT NULL,
            action TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (entry_id) REFERENCES shift_entries(id)
          )
        ''');
        await db.execute('''
          CREATE TABLE mines (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            subsidiary_name TEXT,
            latitude REAL,
            longitude REAL
          )
        ''');
        await db.execute('''
          CREATE TABLE key_value (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
          )
        ''');
      },
    );
  }

  static Future<void> upsertEntry(ShiftEntry entry) async {
    final db = await database;
    await db.insert(
      'shift_entries',
      {
        'id': entry.id,
        'mine_id': entry.mineId,
        'shift_date': entry.shiftDate.toIso8601String(),
        'shift_number': entry.shiftNumber,
        'status': entry.status,
        'submitted_by': entry.submittedBy,
        'submitted_at': entry.submittedAt?.toIso8601String(),
        'values_json': jsonEncode(entry.values),
        'remarks': entry.remarks,
        'is_synced': entry.isSynced ? 1 : 0,
        'updated_at': entry.updatedAt.toIso8601String(),
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  static Future<List<ShiftEntry>> getEntries({String? mineId, String? status}) async {
    final db = await database;
    String where = '1=1';
    List<dynamic> args = [];
    if (mineId != null) {
      where += ' AND mine_id = ?';
      args.add(mineId);
    }
    if (status != null) {
      where += ' AND status = ?';
      args.add(status);
    }
    final rows = await db.query('shift_entries', where: where, whereArgs: args, orderBy: 'shift_date DESC, shift_number');
    return rows.map((r) => ShiftEntry(
          id: r['id'] as String,
          mineId: r['mine_id'] as String,
          shiftDate: DateTime.parse(r['shift_date'] as String),
          shiftNumber: r['shift_number'] as int,
          status: r['status'] as String,
          submittedBy: r['submitted_by'] as String?,
          submittedAt: r['submitted_at'] != null ? DateTime.parse(r['submitted_at'] as String) : null,
          values: r['values_json'] != null ? Map<String, double>.from(jsonDecode(r['values_json'] as String)) : {},
          remarks: r['remarks'] as String?,
          isSynced: (r['is_synced'] as int) == 1,
          updatedAt: DateTime.parse(r['updated_at'] as String),
        )).toList();
  }

  static Future<List<ShiftEntry>> getUnsyncedEntries() async {
    final db = await database;
    final rows = await db.query('shift_entries', where: 'is_synced = 0 AND status = ?', whereArgs: ['submitted']);
    return rows.map((r) => ShiftEntry(
          id: r['id'] as String,
          mineId: r['mine_id'] as String,
          shiftDate: DateTime.parse(r['shift_date'] as String),
          shiftNumber: r['shift_number'] as int,
          status: r['status'] as String,
          values: r['values_json'] != null ? Map<String, double>.from(jsonDecode(r['values_json'] as String)) : {},
          isSynced: false,
          updatedAt: DateTime.parse(r['updated_at'] as String),
        )).toList();
  }

  static Future<void> markSynced(String entryId) async {
    final db = await database;
    await db.update('shift_entries', {'is_synced': 1}, where: 'id = ?', whereArgs: [entryId]);
  }

  static Future<void> saveMines(List<Mine> mines) async {
    final db = await database;
    final batch = db.batch();
    for (final m in mines) {
      batch.insert('mines', {'id': m.id, 'name': m.name, 'subsidiary_name': m.subsidiaryName, 'latitude': m.latitude, 'longitude': m.longitude},
          conflictAlgorithm: ConflictAlgorithm.replace);
    }
    await batch.commit(noResult: true);
  }

  static Future<List<Mine>> getMines() async {
    final db = await database;
    final rows = await db.query('mines');
    return rows.map((r) => Mine.fromJson(r)).toList();
  }

  static Future<void> setKV(String key, String value) async {
    final db = await database;
    await db.insert('key_value', {'key': key, 'value': value}, conflictAlgorithm: ConflictAlgorithm.replace);
  }

  static Future<String?> getKV(String key) async {
    final db = await database;
    final rows = await db.query('key_value', where: 'key = ?', whereArgs: [key]);
    return rows.isNotEmpty ? rows.first['value'] as String : null;
  }
}
