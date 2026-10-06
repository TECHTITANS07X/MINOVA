import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from './client';
import type { ShiftEntry, Report, ConflictFlag, AnomalyFlag, ApprovalTask, Document, Mine, LineageNode } from '../types';

export function useMines() {
  return useQuery<Mine[]>({
    queryKey: ['mines'],
    queryFn: () => api.get('/admin/mines').then(r => r.data),
  });
}

export function useShiftEntries(mineId?: string, status?: string) {
  return useQuery<ShiftEntry[]>({
    queryKey: ['entries', mineId, status],
    queryFn: () => api.get('/entries', { params: { mine_id: mineId, status } }).then(r => r.data.items ?? r.data),
    enabled: !!mineId,
  });
}

export function useReports(mineId?: string) {
  return useQuery<Report[]>({
    queryKey: ['reports', mineId],
    queryFn: () => api.get('/reports', { params: { mine_id: mineId } }).then(r => r.data.items ?? r.data),
  });
}

export function useApprovalInbox() {
  return useQuery<ApprovalTask[]>({
    queryKey: ['approval-inbox'],
    // cursor-paginated endpoints return {items, total, cursor, has_more}
    queryFn: () => api.get('/approval/inbox').then(r => r.data.items ?? r.data),
  });
}

export function useConflicts(status?: string) {
  return useQuery<ConflictFlag[]>({
    queryKey: ['conflicts', status],
    queryFn: () => api.get('/conflicts', { params: { status } }).then(r => r.data.items ?? r.data),
  });
}

export function useDocuments(mineId?: string) {
  return useQuery<Document[]>({
    queryKey: ['documents', mineId],
    queryFn: () => api.get('/documents', { params: { mine_id: mineId } }).then(r => r.data.items ?? r.data),
  });
}

export function useAnomalies(mineId?: string) {
  return useQuery<AnomalyFlag[]>({
    queryKey: ['anomalies', mineId],
    // /anomalies returns a cursor-paginated envelope {items, total, cursor}
    queryFn: () => api.get('/anomalies', { params: { mine_id: mineId } }).then(r => r.data.items ?? r.data),
  });
}

export function useLineageTree(reportValueId: string) {
  return useQuery<LineageNode>({
    queryKey: ['lineage', reportValueId],
    queryFn: () => api.get(`/lineage/${reportValueId}`).then(r => r.data),
    enabled: !!reportValueId,
  });
}

export function useApproveAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { taskId: string; action: string; comment: string }) =>
      api.post(`/approval/${data.taskId}/${data.action}`, { comment: data.comment }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['approval-inbox'] }),
  });
}

export function useResolveConflict() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { conflictId: string; resolution: string; reason: string; value?: number }) =>
      api.post(`/conflicts/${data.conflictId}/resolve`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['conflicts'] }),
  });
}

// ── Innovations (plan Tier 1-3 features) ─────────────────────────────────────

export function usePQPatterns() {
  return useQuery<any[]>({
    queryKey: ['pq-patterns'],
    queryFn: () => api.get('/pq/patterns').then(r => r.data),
  });
}

export function usePQPacks(status?: string) {
  return useQuery<any[]>({
    queryKey: ['pq-packs', status],
    queryFn: () => api.get('/pq/packs', { params: { status } }).then(r => r.data),
  });
}

export function useGeneratePQPacks() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (limit: number) => api.post('/pq/packs/generate', { limit }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pq-packs'] }),
  });
}

export function useQualityPredictions() {
  return useQuery<any[]>({
    queryKey: ['quality-predictions'],
    queryFn: () => api.get('/quality/predictions').then(r => r.data),
  });
}

export function useQualitySummary() {
  return useQuery<any>({
    queryKey: ['quality-summary'],
    queryFn: () => api.get('/quality/summary').then(r => r.data),
  });
}

export function useLossLedgerSummary() {
  return useQuery<any>({
    queryKey: ['loss-ledger-summary'],
    queryFn: () => api.get('/loss-ledger/summary').then(r => r.data),
  });
}

export function useHandovers() {
  return useQuery<any[]>({
    queryKey: ['handovers'],
    queryFn: () => api.get('/handover').then(r => r.data),
  });
}

export function useGenerateHandover() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { mineId: string; shiftNumber: string }) =>
      api.post('/handover/generate', { mine_id: data.mineId, shift_date: new Date().toISOString(), shift_number: data.shiftNumber }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['handovers'] }),
  });
}

export function useComplianceSync() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post('/compliance/sync'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['compliance-filings'] }),
  });
}

export function useComplianceFilings() {
  return useQuery<any[]>({
    queryKey: ['compliance-filings'],
    queryFn: () => api.get('/compliance/filings').then(r => r.data),
  });
}

export function useExplosivesAnalysis() {
  return useQuery<any>({
    queryKey: ['explosives-analysis'],
    queryFn: () => api.post('/explosives/analyze').then(r => r.data),
  });
}

export function useGeologyDeviations() {
  return useQuery<any>({
    queryKey: ['geology-deviations'],
    queryFn: () => api.get('/geology/deviations').then(r => r.data),
  });
}

export function useAnomalyNarrative(anomalyId?: string) {
  return useQuery<any>({
    queryKey: ['anomaly-narrative', anomalyId],
    queryFn: () => api.get(`/anomalies/${anomalyId}/narrative`).then(r => r.data),
    enabled: !!anomalyId,
  });
}

// ── Dashboard / Admin aggregations ──────────────────────────────────────────

export function useDashboard(mineId?: string) {
  return useQuery<any>({
    queryKey: ['dashboard', mineId],
    queryFn: () => api.get('/admin/dashboard', { params: { mine_id: mineId } }).then(r => r.data),
    refetchInterval: 60_000,
  });
}

export function useNotifications(mineId?: string) {
  return useQuery<any[]>({
    queryKey: ['notifications', mineId],
    queryFn: () => api.get('/admin/notifications', { params: { mine_id: mineId } }).then(r => r.data),
    refetchInterval: 30_000,
  });
}

export function useAuditEvents(params?: { action?: string; actor?: string; limit?: number }) {
  return useQuery<any>({
    queryKey: ['audit-events', params],
    queryFn: () => api.get('/admin/audit', { params }).then(r => r.data),
  });
}

export function useInsights(mineId?: string, months?: number) {
  return useQuery<any>({
    queryKey: ['insights', mineId, months],
    queryFn: () => api.get('/admin/insights', { params: { mine_id: mineId, months } }).then(r => r.data),
  });
}

export function useUsers() {
  return useQuery<any[]>({
    queryKey: ['users'],
    queryFn: () => api.get('/admin/users').then(r => r.data),
  });
}

export function useApprovalChains(mineId?: string) {
  return useQuery<any[]>({
    queryKey: ['approval-chains', mineId],
    queryFn: () => api.get('/admin/approval-chains', { params: { mine_id: mineId } }).then(r => r.data),
  });
}

export function useSystemHealth() {
  return useQuery<any>({
    queryKey: ['system-health'],
    queryFn: () => api.get('/admin/health').then(r => r.data),
    refetchInterval: 30_000,
  });
}

// ── Weather & Recovery ──────────────────────────────────────────────────────

export function useWeatherForecast(mineId?: string) {
  return useQuery<any[]>({
    queryKey: ['weather-forecast', mineId],
    queryFn: () => api.get(`/weather/forecast/${mineId}`).then(r => r.data),
    enabled: !!mineId,
  });
}

export function useWeatherObservations(mineId?: string) {
  return useQuery<any[]>({
    queryKey: ['weather-observations', mineId],
    queryFn: () => api.get(`/weather/observations/${mineId}`).then(r => r.data),
    enabled: !!mineId,
  });
}

export function useRecoveryPlans(mineId?: string) {
  return useQuery<any[]>({
    queryKey: ['recovery-plans', mineId],
    queryFn: () => api.get(`/weather/recovery-plans/${mineId}`).then(r => r.data),
    enabled: !!mineId,
  });
}

// ── Data Entry mutations ────────────────────────────────────────────────────

export function useCreateEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: any) => api.post('/entries', data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['entries'] }),
  });
}

export function useSubmitEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (entryId: string) => api.post(`/entries/${entryId}/submit`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['entries'] }),
  });
}

export function useGenerateReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { mine_id: string; period: string; period_start: string; period_end: string }) =>
      api.post('/reports/generate', data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['reports'] }),
  });
}

// ── Tier-4 Innovations ──────────────────────────────────────────────────────

export function useMeetingActions(mineId?: string) {
  return useQuery<any[]>({
    queryKey: ['meeting-actions', mineId],
    queryFn: () => api.get('/meetings/actions', { params: { mine_id: mineId } }).then(r => r.data),
  });
}

export function useCreateMeetingAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: any) => api.post('/meetings/actions', data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['meeting-actions'] }),
  });
}

export function useKnowledgeEntries(mineId?: string) {
  return useQuery<any[]>({
    queryKey: ['knowledge-entries', mineId],
    queryFn: () => api.get('/knowledge/entries', { params: { mine_id: mineId } }).then(r => r.data),
  });
}

export function useCreateKnowledgeEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: any) => api.post('/knowledge/entries', data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['knowledge-entries'] }),
  });
}

export function useSafetyIncidents(mineId?: string) {
  return useQuery<any[]>({
    queryKey: ['safety-incidents', mineId],
    queryFn: () => api.get('/safety/incidents', { params: { mine_id: mineId } }).then(r => r.data),
  });
}

export function useSafetyPatterns() {
  return useQuery<any[]>({
    queryKey: ['safety-patterns'],
    queryFn: () => api.get('/safety/patterns').then(r => r.data),
  });
}

export function usePhotoVerifications(mineId?: string) {
  return useQuery<any[]>({
    queryKey: ['photo-verifications', mineId],
    queryFn: () => api.get('/photos/verifications', { params: { mine_id: mineId } }).then(r => r.data),
  });
}

export function useUploadPhotoEvidence() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) =>
      api.post('/photos/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['photo-verifications'] }),
  });
}

// ── Dashboard / Admin / Insights ─────────────────────────────────────────────

export function useDashboardSummary(mineId?: string) {
  return useQuery<any>({
    queryKey: ['dashboard-summary', mineId],
    queryFn: () => api.get('/admin/dashboard', { params: { mine_id: mineId } }).then(r => r.data),
  });
}

export function useNotificationsFeed(mineId?: string) {
  return useQuery<any[]>({
    queryKey: ['notifications-feed', mineId],
    queryFn: () => api.get('/admin/notifications', { params: { mine_id: mineId } }).then(r => r.data),
    refetchInterval: 60_000,
  });
}

export function useInsightsData(mineId?: string) {
  return useQuery<any>({
    queryKey: ['insights', mineId],
    queryFn: () => api.get('/admin/insights', { params: { mine_id: mineId } }).then(r => r.data),
  });
}

export function useBenches(mineId?: string) {
  return useQuery<any[]>({
    queryKey: ['benches', mineId],
    queryFn: () => api.get(`/admin/benches/${mineId}`).then(r => r.data),
    enabled: !!mineId,
  });
}

export function useReportTemplates() {
  return useQuery<any[]>({
    queryKey: ['report-templates'],
    queryFn: () => api.get('/admin/report-templates').then(r => r.data),
  });
}
