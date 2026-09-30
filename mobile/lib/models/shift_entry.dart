class ShiftEntry {
  final String id;
  final String mineId;
  final DateTime shiftDate;
  final int shiftNumber;
  final String status;
  final String? submittedBy;
  final DateTime? submittedAt;
  final Map<String, double> values;
  final String? remarks;
  final bool isSynced;
  final DateTime updatedAt;

  ShiftEntry({
    required this.id,
    required this.mineId,
    required this.shiftDate,
    required this.shiftNumber,
    this.status = 'draft',
    this.submittedBy,
    this.submittedAt,
    this.values = const {},
    this.remarks,
    this.isSynced = false,
    DateTime? updatedAt,
  }) : updatedAt = updatedAt ?? DateTime.now();

  Map<String, dynamic> toJson() => {
        'id': id,
        'mine_id': mineId,
        'shift_date': shiftDate.toIso8601String(),
        'shift_number': shiftNumber,
        'status': status,
        'submitted_by': submittedBy,
        'submitted_at': submittedAt?.toIso8601String(),
        'values': values,
        'remarks': remarks,
        'is_synced': isSynced,
        'updated_at': updatedAt.toIso8601String(),
      };

  factory ShiftEntry.fromJson(Map<String, dynamic> json) => ShiftEntry(
        id: json['id'],
        mineId: json['mine_id'],
        shiftDate: DateTime.parse(json['shift_date']),
        shiftNumber: json['shift_number'],
        status: json['status'] ?? 'draft',
        submittedBy: json['submitted_by'],
        submittedAt: json['submitted_at'] != null ? DateTime.parse(json['submitted_at']) : null,
        values: Map<String, double>.from(json['values'] ?? {}),
        remarks: json['remarks'],
        isSynced: json['is_synced'] ?? false,
        updatedAt: json['updated_at'] != null ? DateTime.parse(json['updated_at']) : DateTime.now(),
      );

  ShiftEntry copyWith({
    String? status,
    Map<String, double>? values,
    String? remarks,
    bool? isSynced,
  }) =>
      ShiftEntry(
        id: id,
        mineId: mineId,
        shiftDate: shiftDate,
        shiftNumber: shiftNumber,
        status: status ?? this.status,
        submittedBy: submittedBy,
        submittedAt: submittedAt,
        values: values ?? this.values,
        remarks: remarks ?? this.remarks,
        isSynced: isSynced ?? this.isSynced,
        updatedAt: DateTime.now(),
      );
}

class Mine {
  final String id;
  final String name;
  final String subsidiaryName;
  final double latitude;
  final double longitude;

  Mine({required this.id, required this.name, required this.subsidiaryName, required this.latitude, required this.longitude});

  factory Mine.fromJson(Map<String, dynamic> json) => Mine(
        id: json['id'],
        name: json['name'],
        subsidiaryName: json['subsidiary_name'] ?? '',
        latitude: (json['latitude'] ?? 0).toDouble(),
        longitude: (json['longitude'] ?? 0).toDouble(),
      );
}
