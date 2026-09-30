import 'package:connectivity_plus/connectivity_plus.dart';
import '../models/shift_entry.dart';
import 'local_db.dart';
import 'api_service.dart';

class SyncService {
  static Future<bool> isOnline() async {
    final result = await Connectivity().checkConnectivity();
    return result.contains(ConnectivityResult.wifi) || result.contains(ConnectivityResult.mobile);
  }

  static Future<SyncResult> syncAll(String deviceId) async {
    if (!await isOnline()) {
      return SyncResult(pushed: 0, pulled: 0, conflicts: 0, offline: true);
    }

    int pushed = 0;
    int pulled = 0;
    int conflicts = 0;

    final unsynced = await LocalDb.getUnsyncedEntries();
    if (unsynced.isNotEmpty) {
      try {
        final result = await ApiService.pushBatch(unsynced, deviceId);
        pushed = result['accepted'] ?? 0;
        conflicts = (result['conflicts'] as List?)?.length ?? 0;
        for (final entry in unsynced) {
          if (pushed > 0) {
            await LocalDb.markSynced(entry.id);
          }
        }
      } catch (_) {}
    }

    try {
      final cursor = await LocalDb.getKV('sync_cursor');
      final mines = await LocalDb.getMines();
      for (final mine in mines) {
        final delta = await ApiService.pullDelta(mine.id, cursor);
        final entries = (delta['entries'] as List?) ?? [];
        for (final e in entries) {
          await LocalDb.upsertEntry(ShiftEntry.fromJson(e));
          pulled++;
        }
        if (delta['cursor'] != null) {
          await LocalDb.setKV('sync_cursor', delta['cursor']);
        }
      }
    } catch (_) {}

    return SyncResult(pushed: pushed, pulled: pulled, conflicts: conflicts, offline: false);
  }
}

class SyncResult {
  final int pushed;
  final int pulled;
  final int conflicts;
  final bool offline;

  SyncResult({required this.pushed, required this.pulled, required this.conflicts, required this.offline});
}
