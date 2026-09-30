import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import 'entry_form_screen.dart';

class EntriesListScreen extends StatelessWidget {
  const EntriesListScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final entries = state.entries;

    if (state.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (entries.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.inbox, size: 64, color: Colors.grey.shade400),
            const SizedBox(height: 16),
            const Text('No entries yet', style: TextStyle(fontSize: 18, color: Colors.grey)),
            const SizedBox(height: 8),
            const Text('Tap + to create a shift entry'),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: state.refreshEntries,
      child: ListView.builder(
        padding: const EdgeInsets.all(8),
        itemCount: entries.length,
        itemBuilder: (context, i) {
          final e = entries[i];
          final production = e.values['production_tonnes'];
          return Card(
            child: ListTile(
              leading: CircleAvatar(
                backgroundColor: _statusColor(e.status),
                child: Text('S${e.shiftNumber}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
              ),
              title: Text('${e.shiftDate.toString().substring(0, 10)} — Shift ${e.shiftNumber}'),
              subtitle: Text(
                '${production?.toStringAsFixed(0) ?? '-'} tonnes | ${e.status}${e.isSynced ? '' : ' (not synced)'}',
              ),
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (!e.isSynced)
                    Icon(Icons.cloud_off, size: 16, color: Colors.orange.shade300),
                  if (e.status == 'draft')
                    IconButton(
                      icon: const Icon(Icons.edit),
                      onPressed: () => Navigator.push(
                        context,
                        MaterialPageRoute(builder: (_) => EntryFormScreen(existing: e)),
                      ),
                    ),
                  if (e.status == 'draft')
                    IconButton(
                      icon: const Icon(Icons.send, color: Colors.blue),
                      onPressed: () => state.submitEntry(e.id),
                    ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'approved':
        return Colors.green;
      case 'submitted':
        return Colors.blue;
      case 'returned':
        return Colors.red;
      default:
        return Colors.orange;
    }
  }
}
