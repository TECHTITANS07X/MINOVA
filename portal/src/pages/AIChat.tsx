import { useState, useRef, useEffect } from 'react';
import {
  Box, Card, CardContent, Typography, TextField, IconButton, Paper, Chip, Divider,
  Drawer, List, ListItemButton, ListItemText, Button, CircularProgress,
} from '@mui/material';
import { Send, AttachFile, Download, OpenInNew, Close } from '@mui/icons-material';
import { api } from '../api/client';
import type { ChatMessage, Citation } from '../types';

function CitationChip({ citation, onClick }: { citation: Citation; onClick: () => void }) {
  return (
    <Chip size="small" label={`[${citation.label}]`} variant="outlined" color="primary"
      onClick={onClick} clickable sx={{ mr: 0.5, mb: 0.5 }} icon={<OpenInNew sx={{ fontSize: 14 }} />} />
  );
}

function MessageBubble({ msg, onCitationClick }: { msg: ChatMessage; onCitationClick: (c: Citation) => void }) {
  const isUser = msg.role === 'user';
  return (
    <Box display="flex" justifyContent={isUser ? 'flex-end' : 'flex-start'} mb={2}>
      <Paper elevation={1} sx={{
        p: 2, maxWidth: '75%', borderRadius: 2,
        bgcolor: isUser ? 'primary.main' : 'background.paper',
        color: isUser ? 'primary.contrastText' : 'text.primary',
      }}>
        {msg.route_type && !isUser && (
          <Chip size="small" label={msg.route_type} sx={{ mb: 1 }} variant="outlined" />
        )}
        <Typography variant="body2" whiteSpace="pre-wrap">{msg.content}</Typography>
        {msg.citations && msg.citations.length > 0 && (
          <Box mt={1}>
            <Divider sx={{ my: 1 }} />
            <Typography variant="caption" color="text.secondary" display="block" mb={0.5}>Sources:</Typography>
            {msg.citations.map((c, i) => (
              <CitationChip key={i} citation={c} onClick={() => onCitationClick(c)} />
            ))}
          </Box>
        )}
      </Paper>
    </Box>
  );
}

export default function AIChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const userMsg: ChatMessage = {
      id: Date.now().toString(), role: 'user', content: input,
      route_type: null, citations: null, created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await api.post('/chat/message', { content: input, session_id: null });
      setMessages(prev => [...prev, res.data]);
    } catch {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(), role: 'assistant',
        content: 'Sorry, I encountered an error processing your question. Please try again.',
        route_type: null, citations: null, created_at: new Date().toISOString(),
      }]);
    }
    setLoading(false);
  };

  return (
    <Box display="flex" height="calc(100vh - 100px)">
      <Box flex={1} display="flex" flexDirection="column">
        <Typography variant="h5" gutterBottom>AI Assistant</Typography>
        <Typography variant="body2" color="text.secondary" mb={2}>
          Ask questions about production, targets, causes, or search documents. Every answer comes with citations.
        </Typography>

        <Card sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <CardContent sx={{ flex: 1, overflow: 'auto', pb: 0 }}>
            {messages.length === 0 && (
              <Box textAlign="center" py={8}>
                <Typography variant="h6" color="text.secondary" gutterBottom>Ask anything about your mines</Typography>
                <Box display="flex" gap={1} justifyContent="center" flexWrap="wrap">
                  {['Why was September production low?', 'Show target vs actual for Q3',
                    'What equipment failures occurred this month?', 'Summarize the latest geological report'
                  ].map((q) => (
                    <Chip key={q} label={q} onClick={() => setInput(q)} clickable variant="outlined" />
                  ))}
                </Box>
              </Box>
            )}
            {messages.map((msg) => (
              <MessageBubble key={msg.id} msg={msg}
                onCitationClick={(c) => { setSelectedCitation(c); setEvidenceOpen(true); }} />
            ))}
            {loading && (
              <Box display="flex" alignItems="center" gap={1} mb={2}>
                <CircularProgress size={16} />
                <Typography variant="body2" color="text.secondary">Analyzing...</Typography>
              </Box>
            )}
            <div ref={bottomRef} />
          </CardContent>

          <Box p={2} borderTop={1} borderColor="divider" display="flex" gap={1}>
            <TextField fullWidth size="small" placeholder="Ask a question..."
              value={input} onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }} />
            <IconButton color="primary" onClick={sendMessage} disabled={loading || !input.trim()}>
              <Send />
            </IconButton>
          </Box>
        </Card>
      </Box>

      <Drawer anchor="right" open={evidenceOpen} onClose={() => setEvidenceOpen(false)}
        PaperProps={{ sx: { width: 400 } }}>
        <Box p={2}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">Evidence</Typography>
            <IconButton onClick={() => setEvidenceOpen(false)}><Close /></IconButton>
          </Box>
          {selectedCitation && (
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle2">{selectedCitation.label}</Typography>
                <Typography variant="body2" color="text.secondary" mt={1}>
                  Type: {selectedCitation.type}
                  {selectedCitation.page && ` | Page ${selectedCitation.page}`}
                  {selectedCitation.value !== undefined && ` | Value: ${selectedCitation.value}`}
                </Typography>
                <Button variant="outlined" size="small" startIcon={<OpenInNew />} sx={{ mt: 2 }}>
                  Open Source
                </Button>
              </CardContent>
            </Card>
          )}
        </Box>
      </Drawer>
    </Box>
  );
}
