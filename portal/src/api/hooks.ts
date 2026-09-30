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
    queryFn: () => api.get('/entries', { params: { mine_id: mineId, status } }).then(r => r.data),
    enabled: !!mineId,
  });
}

export function useReports(mineId?: string) {
  return useQuery<Report[]>({
    queryKey: ['reports', mineId],
    queryFn: () => api.get('/reports', { params: { mine_id: mineId } }).then(r => r.data),
  });
}

export function useApprovalInbox() {
  return useQuery<ApprovalTask[]>({
    queryKey: ['approval-inbox'],
    queryFn: () => api.get('/approval/inbox').then(r => r.data),
  });
}

export function useConflicts(status?: string) {
  return useQuery<ConflictFlag[]>({
    queryKey: ['conflicts', status],
    queryFn: () => api.get('/conflicts', { params: { status } }).then(r => r.data),
  });
}

export function useDocuments(mineId?: string) {
  return useQuery<Document[]>({
    queryKey: ['documents', mineId],
    queryFn: () => api.get('/documents', { params: { mine_id: mineId } }).then(r => r.data),
  });
}

export function useAnomalies(mineId?: string) {
  return useQuery<AnomalyFlag[]>({
    queryKey: ['anomalies', mineId],
    queryFn: () => api.get('/anomalies', { params: { mine_id: mineId } }).then(r => r.data),
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
