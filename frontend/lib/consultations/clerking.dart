import 'package:flutter/material.dart';

import '../api.dart';

/// The Nigerian clerking proforma.
///
/// The 13 sections, their order, labels and placeholders all come from
/// `/consultations/api/clerking-notes/schema/` — the server owns the proforma,
/// so this screen cannot drift out of step with the web form.
class ClerkingScreen extends StatefulWidget {
  const ClerkingScreen({
    super.key,
    required this.consultation,
    this.note,
  });

  final Map<String, dynamic> consultation;

  /// An existing note to extend, or null to start one.
  final Map<String, dynamic>? note;

  @override
  State<ClerkingScreen> createState() => _ClerkingScreenState();
}

class _ClerkingScreenState extends State<ClerkingScreen> {
  List<Map<String, dynamic>>? _schema;
  final Map<String, TextEditingController> _fields = {};
  String? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _loadSchema();
  }

  @override
  void dispose() {
    for (final controller in _fields.values) {
      controller.dispose();
    }
    super.dispose();
  }

  Future<void> _loadSchema() async {
    try {
      final schema =
          await Api.get('/consultations/api/clerking-notes/schema/') as List;
      if (!mounted) return;
      setState(() {
        _schema = schema.cast<Map<String, dynamic>>();
        for (final section in _schema!) {
          final name = '${section['name']}';
          _fields[name] = TextEditingController(
            text: '${widget.note?[name] ?? ''}',
          );
        }
      });
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  Future<void> _save() async {
    // Send only the sections with content: a blank one means "not recorded at
    // this visit", and must not wipe what an earlier visit wrote.
    final payload = <String, dynamic>{
      'consultation': widget.consultation['id'],
    };
    _fields.forEach((name, controller) {
      final value = controller.text.trim();
      if (value.isNotEmpty) payload[name] = value;
    });

    if (payload.length == 1) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Nothing to save yet')),
      );
      return;
    }

    setState(() => _busy = true);
    try {
      if (widget.note == null) {
        await Api.post('/consultations/api/clerking-notes/', payload);
      } else {
        await Api.patch(
          '/consultations/api/clerking-notes/${widget.note!['id']}/',
          payload,
        );
      }
      if (mounted) Navigator.pop(context, true);
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final schema = _schema;
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.note == null ? 'Clerking note' : 'Continue note'),
        bottom: _busy
            ? const PreferredSize(
                preferredSize: Size.fromHeight(2),
                child: LinearProgressIndicator(),
              )
            : null,
      ),
      body: _error != null
          ? Center(child: Text(_error!))
          : schema == null
              ? const Center(child: CircularProgressIndicator())
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    Text(
                      '${widget.consultation['patient_name']} '
                      '(${widget.consultation['patient_number']})',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Fill in what applies — sections left blank are simply '
                      'not recorded.',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    const SizedBox(height: 16),
                    for (final section in schema) ...[
                      TextField(
                        controller: _fields['${section['name']}'],
                        maxLines: (section['rows'] as int?) ?? 2,
                        decoration: InputDecoration(
                          labelText: '${section['label']}',
                          hintText: '${section['placeholder']}',
                          border: const OutlineInputBorder(),
                          alignLabelWithHint: true,
                        ),
                      ),
                      const SizedBox(height: 14),
                    ],
                    FilledButton(
                      onPressed: _busy ? null : _save,
                      child: Text(
                        widget.note == null ? 'Save note' : 'Update note',
                      ),
                    ),
                  ],
                ),
    );
  }
}

/// Read-only history of clerking notes for one consultation.
class ClerkingHistoryScreen extends StatefulWidget {
  const ClerkingHistoryScreen({super.key, required this.consultation});

  final Map<String, dynamic> consultation;

  @override
  State<ClerkingHistoryScreen> createState() => _ClerkingHistoryScreenState();
}

class _ClerkingHistoryScreenState extends State<ClerkingHistoryScreen> {
  List<Map<String, dynamic>>? _notes;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final data = await Api.get(
        '/consultations/api/clerking-notes/',
        {'consultation': '${widget.consultation['id']}'},
      );
      if (mounted) {
        setState(() {
          _notes = (data['results'] as List).cast<Map<String, dynamic>>();
          _error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  Future<void> _open({Map<String, dynamic>? note}) async {
    final saved = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => ClerkingScreen(
          consultation: widget.consultation,
          note: note,
        ),
      ),
    );
    if (saved == true) _load();
  }

  @override
  Widget build(BuildContext context) {
    final notes = _notes;
    return Scaffold(
      appBar: AppBar(title: const Text('Clerking notes')),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _open(),
        child: const Icon(Icons.note_add),
      ),
      body: _error != null
          ? Center(child: Text(_error!))
          : notes == null
              ? const Center(child: CircularProgressIndicator())
              : notes.isEmpty
                  ? const Center(child: Text('No clerking notes yet'))
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView(
                        children: [
                          for (final note in notes)
                            ExpansionTile(
                              title: Text(
                                '${note['created_at'].toString().split('T').first}'
                                ' · ${note['created_by_name']}',
                              ),
                              subtitle: Text(
                                '${(note['sections'] as List).length} section(s)',
                              ),
                              children: [
                                for (final section
                                    in (note['sections'] as List)
                                        .cast<Map<String, dynamic>>())
                                  ListTile(
                                    title: Text(
                                      '${section['label']}',
                                      style: Theme.of(context)
                                          .textTheme
                                          .labelMedium,
                                    ),
                                    subtitle: Text('${section['value']}'),
                                  ),
                                Padding(
                                  padding: const EdgeInsets.all(12),
                                  child: OutlinedButton(
                                    onPressed: () => _open(note: note),
                                    child: const Text('Add to this note'),
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
