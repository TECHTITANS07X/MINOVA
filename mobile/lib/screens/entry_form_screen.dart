import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:uuid/uuid.dart';
import '../models/shift_entry.dart';
import '../providers/app_state.dart';

class EntryFormScreen extends StatefulWidget {
  final ShiftEntry? existing;
  const EntryFormScreen({super.key, this.existing});

  @override
  State<EntryFormScreen> createState() => _EntryFormScreenState();
}

class _EntryFormScreenState extends State<EntryFormScreen> {
  final _formKey = GlobalKey<FormState>();
  int _shift = 1;
  DateTime _date = DateTime.now();
  final _production = TextEditingController();
  final _ob = TextEditingController();
  final _hours = TextEditingController();
  final _workers = TextEditingController();
  final _remarks = TextEditingController();

  @override
  void initState() {
    super.initState();
    if (widget.existing != null) {
      final e = widget.existing!;
      _shift = e.shiftNumber;
      _date = e.shiftDate;
      _production.text = (e.values['production_tonnes'] ?? '').toString();
      _ob.text = (e.values['ob_volume_m3'] ?? '').toString();
      _hours.text = (e.values['operating_hours'] ?? '').toString();
      _workers.text = (e.values['workers_present'] ?? '').toString();
      _remarks.text = e.remarks ?? '';
    }
  }

  @override
  void dispose() {
    _production.dispose();
    _ob.dispose();
    _hours.dispose();
    _workers.dispose();
    _remarks.dispose();
    super.dispose();
  }

  Future<void> _save({bool submit = false}) async {
    if (!_formKey.currentState!.validate()) return;
    final state = context.read<AppState>();
    final entry = ShiftEntry(
      id: widget.existing?.id ?? const Uuid().v4(),
      mineId: state.selectedMineId ?? '',
      shiftDate: _date,
      shiftNumber: _shift,
      status: submit ? 'submitted' : 'draft',
      values: {
        'production_tonnes': double.tryParse(_production.text) ?? 0,
        'ob_volume_m3': double.tryParse(_ob.text) ?? 0,
        'operating_hours': double.tryParse(_hours.text) ?? 0,
        'workers_present': double.tryParse(_workers.text) ?? 0,
      },
      remarks: _remarks.text.isEmpty ? null : _remarks.text,
    );
    await state.saveEntry(entry);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(submit ? 'Entry submitted' : 'Draft saved')),
      );
      Navigator.pop(context);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.existing != null ? 'Edit Entry' : 'New Shift Entry')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Shift Details', style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: InkWell(
                            onTap: () async {
                              final d = await showDatePicker(context: context, firstDate: DateTime(2024), lastDate: DateTime.now(), initialDate: _date);
                              if (d != null) setState(() => _date = d);
                            },
                            child: InputDecorator(
                              decoration: const InputDecoration(labelText: 'Date', border: OutlineInputBorder()),
                              child: Text(_date.toString().substring(0, 10)),
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: DropdownButtonFormField<int>(
                            value: _shift,
                            decoration: const InputDecoration(labelText: 'Shift', border: OutlineInputBorder()),
                            items: const [
                              DropdownMenuItem(value: 1, child: Text('Shift 1 (6-14h)')),
                              DropdownMenuItem(value: 2, child: Text('Shift 2 (14-22h)')),
                              DropdownMenuItem(value: 3, child: Text('Shift 3 (22-6h)')),
                            ],
                            onChanged: (v) => setState(() => _shift = v ?? 1),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Production Data', style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _production,
                      decoration: const InputDecoration(labelText: 'Production (tonnes)', border: OutlineInputBorder(), suffixText: 't'),
                      keyboardType: TextInputType.number,
                      validator: (v) => v == null || v.isEmpty ? 'Required' : null,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _ob,
                      decoration: const InputDecoration(labelText: 'Overburden (m³)', border: OutlineInputBorder(), suffixText: 'm³'),
                      keyboardType: TextInputType.number,
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            controller: _hours,
                            decoration: const InputDecoration(labelText: 'Operating Hours', border: OutlineInputBorder()),
                            keyboardType: TextInputType.number,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextFormField(
                            controller: _workers,
                            decoration: const InputDecoration(labelText: 'Workers', border: OutlineInputBorder()),
                            keyboardType: TextInputType.number,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _remarks,
              decoration: const InputDecoration(labelText: 'Remarks (optional)', border: OutlineInputBorder()),
              maxLines: 3,
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _save(submit: false),
                    icon: const Icon(Icons.save),
                    label: const Text('Save Draft'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: FilledButton.icon(
                    onPressed: () => _save(submit: true),
                    icon: const Icon(Icons.send),
                    label: const Text('Submit'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
