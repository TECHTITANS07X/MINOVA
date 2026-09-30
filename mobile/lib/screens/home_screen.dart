import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import 'entry_form_screen.dart';
import 'entries_list_screen.dart';
import 'sync_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _currentIndex = 0;

  final _pages = const [
    _DashboardTab(),
    EntriesListScreen(),
    SyncScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    return Scaffold(
      appBar: AppBar(
        title: const Text('MINOVA'),
        actions: [
          if (state.isOnline)
            const Icon(Icons.cloud_done, color: Colors.green)
          else
            const Icon(Icons.cloud_off, color: Colors.orange),
          const SizedBox(width: 8),
          if (state.mines.length > 1)
            PopupMenuButton<String>(
              icon: const Icon(Icons.location_on),
              onSelected: state.selectMine,
              itemBuilder: (_) => state.mines
                  .map((m) => PopupMenuItem(value: m.id, child: Text(m.name)))
                  .toList(),
            ),
          const SizedBox(width: 8),
        ],
      ),
      body: _pages[_currentIndex],
      floatingActionButton: _currentIndex == 1
          ? FloatingActionButton(
              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const EntryFormScreen())),
              child: const Icon(Icons.add),
            )
          : null,
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (i) => setState(() => _currentIndex = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.dashboard), label: 'Dashboard'),
          NavigationDestination(icon: Icon(Icons.edit_note), label: 'Entries'),
          NavigationDestination(icon: Icon(Icons.sync), label: 'Sync'),
        ],
      ),
    );
  }
}

class _DashboardTab extends StatelessWidget {
  const _DashboardTab();

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final mine = state.selectedMine;
    final entries = state.entries;
    final drafts = entries.where((e) => e.status == 'draft').length;
    final submitted = entries.where((e) => e.status == 'submitted').length;
    final approved = entries.where((e) => e.status == 'approved').length;
    final unsynced = entries.where((e) => !e.isSynced && e.status == 'submitted').length;

    return RefreshIndicator(
      onRefresh: state.refreshEntries,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (mine != null)
            Card(
              child: ListTile(
                leading: const Icon(Icons.factory, size: 40),
                title: Text(mine.name, style: Theme.of(context).textTheme.titleLarge),
                subtitle: Text(mine.subsidiaryName),
              ),
            ),
          const SizedBox(height: 16),
          Row(
            children: [
              _StatCard(label: 'Drafts', value: '$drafts', color: Colors.orange),
              const SizedBox(width: 8),
              _StatCard(label: 'Submitted', value: '$submitted', color: Colors.blue),
              const SizedBox(width: 8),
              _StatCard(label: 'Approved', value: '$approved', color: Colors.green),
            ],
          ),
          const SizedBox(height: 8),
          if (unsynced > 0)
            Card(
              color: Colors.amber.shade50,
              child: ListTile(
                leading: const Icon(Icons.cloud_upload, color: Colors.amber),
                title: Text('$unsynced entries pending sync'),
                trailing: TextButton(
                  onPressed: () => state.sync(),
                  child: const Text('Sync Now'),
                ),
              ),
            ),
          const SizedBox(height: 16),
          Text('Recent Entries', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          ...entries.take(5).map((e) => Card(
                child: ListTile(
                  title: Text('Shift ${e.shiftNumber} — ${e.shiftDate.toString().substring(0, 10)}'),
                  subtitle: Text('${e.values['production_tonnes']?.toStringAsFixed(0) ?? '-'} tonnes'),
                  trailing: Chip(
                    label: Text(e.status),
                    backgroundColor: e.status == 'approved' ? Colors.green.shade100 : e.status == 'submitted' ? Colors.blue.shade100 : Colors.orange.shade100,
                  ),
                ),
              )),
        ],
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String label;
  final String value;
  final Color color;

  const _StatCard({required this.label, required this.value, required this.color});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              Text(value, style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: color)),
              Text(label, style: Theme.of(context).textTheme.bodySmall),
            ],
          ),
        ),
      ),
    );
  }
}
