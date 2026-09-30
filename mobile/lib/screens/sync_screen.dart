import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';

class SyncScreen extends StatelessWidget {
  const SyncScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final lastSync = state.lastSync;

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              children: [
                Icon(
                  state.isOnline ? Icons.cloud_done : Icons.cloud_off,
                  size: 64,
                  color: state.isOnline ? Colors.green : Colors.orange,
                ),
                const SizedBox(height: 16),
                Text(
                  state.isOnline ? 'Online' : 'Offline',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 8),
                Text(
                  state.isOnline
                      ? 'Connected to MINOVA server'
                      : 'Working offline — entries saved locally',
                  style: Theme.of(context).textTheme.bodyMedium,
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        if (lastSync != null) ...[
          Card(
            child: Column(
              children: [
                ListTile(
                  leading: const Icon(Icons.upload),
                  title: const Text('Pushed'),
                  trailing: Text('${lastSync.pushed} entries', style: const TextStyle(fontWeight: FontWeight.bold)),
                ),
                ListTile(
                  leading: const Icon(Icons.download),
                  title: const Text('Pulled'),
                  trailing: Text('${lastSync.pulled} entries', style: const TextStyle(fontWeight: FontWeight.bold)),
                ),
                if (lastSync.conflicts > 0)
                  ListTile(
                    leading: const Icon(Icons.warning, color: Colors.amber),
                    title: const Text('Conflicts'),
                    trailing: Text('${lastSync.conflicts}', style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.amber)),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 16),
        ],
        FilledButton.icon(
          onPressed: state.isLoading ? null : () => state.sync(),
          icon: state.isLoading ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.sync),
          label: Text(state.isLoading ? 'Syncing...' : 'Sync Now'),
          style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48)),
        ),
        const SizedBox(height: 24),
        Text('How Sync Works', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        const Text(
          'MINOVA works fully offline. Shift entries are saved locally on your device. '
          'When you have network connectivity, tap Sync to push your entries to the server '
          'and pull any updates. Conflicts between local and remote data are flagged for '
          'manual resolution — they are never auto-resolved.',
        ),
      ],
    );
  }
}
