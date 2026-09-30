import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';
import '../models/shift_entry.dart';
import '../services/local_db.dart';
import '../services/sync_service.dart';

class AppState extends ChangeNotifier {
  List<ShiftEntry> _entries = [];
  List<Mine> _mines = [];
  bool _isLoading = false;
  bool _isOnline = false;
  String? _selectedMineId;
  String _deviceId = '';
  SyncResult? _lastSync;

  List<ShiftEntry> get entries => _entries;
  List<Mine> get mines => _mines;
  bool get isLoading => _isLoading;
  bool get isOnline => _isOnline;
  String? get selectedMineId => _selectedMineId;
  SyncResult? get lastSync => _lastSync;
  Mine? get selectedMine => _mines.where((m) => m.id == _selectedMineId).firstOrNull;

  Future<void> init() async {
    _deviceId = const Uuid().v4();
    final savedDevice = await LocalDb.getKV('device_id');
    if (savedDevice != null) {
      _deviceId = savedDevice;
    } else {
      await LocalDb.setKV('device_id', _deviceId);
    }
    _mines = await LocalDb.getMines();
    _isOnline = await SyncService.isOnline();
    if (_mines.isNotEmpty) {
      _selectedMineId = _mines.first.id;
    }
    await refreshEntries();
  }

  Future<void> refreshEntries() async {
    _isLoading = true;
    notifyListeners();
    _entries = await LocalDb.getEntries(mineId: _selectedMineId);
    _isLoading = false;
    notifyListeners();
  }

  void selectMine(String mineId) {
    _selectedMineId = mineId;
    refreshEntries();
  }

  Future<void> saveEntry(ShiftEntry entry) async {
    await LocalDb.upsertEntry(entry);
    await refreshEntries();
  }

  Future<void> submitEntry(String entryId) async {
    final entry = _entries.firstWhere((e) => e.id == entryId);
    final updated = entry.copyWith(status: 'submitted');
    await LocalDb.upsertEntry(updated);
    await refreshEntries();
  }

  Future<SyncResult> sync() async {
    _isLoading = true;
    notifyListeners();
    _lastSync = await SyncService.syncAll(_deviceId);
    _isOnline = !_lastSync!.offline;
    await refreshEntries();
    _isLoading = false;
    notifyListeners();
    return _lastSync!;
  }

  Future<void> loadMines(List<Mine> mines) async {
    await LocalDb.saveMines(mines);
    _mines = mines;
    if (_selectedMineId == null && mines.isNotEmpty) {
      _selectedMineId = mines.first.id;
    }
    notifyListeners();
  }
}
