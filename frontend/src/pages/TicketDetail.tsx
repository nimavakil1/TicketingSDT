import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ticketsApi, TicketDetail as TicketDetailType, Ticket, CustomStatus, Attachment } from '../api/tickets';
import { ArrowLeft, AlertTriangle, CheckCircle, XCircle, Clock, MessageSquare, User, Lock, ThumbsUp, ThumbsDown, ChevronLeft, ChevronRight, RefreshCw, Send, Paperclip, Download, Trash2, Upload, Eye, X, ChevronDown, ChevronUp, Truck } from 'lucide-react';
import client from '../api/client';
import { formatInCET } from '../utils/dateFormat';
import { messagesApi, PendingMessage } from '../api/messages';

const TicketDetail: React.FC = () => {
  const { ticketNumber } = useParams<{ ticketNumber: string }>();
  const navigate = useNavigate();
  const [ticket, setTicket] = useState<TicketDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [feedbackDecisionId, setFeedbackDecisionId] = useState<number | null>(null);
  const [feedbackNotes, setFeedbackNotes] = useState('');
  const [savingFeedback, setSavingFeedback] = useState(false);
  const [ticketList, setTicketList] = useState<Ticket[]>([]);
  const [currentIndex, setCurrentIndex] = useState<number>(-1);
  const [reprocessing, setReprocessing] = useState(false);
  const [reprocessMessage, setReprocessMessage] = useState<{type: 'success' | 'error', text: string} | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [composeExpanded, setComposeExpanded] = useState(false);
  const [composeRecipientType, setComposeRecipientType] = useState<'customer' | 'supplier' | 'internal'>('customer');
  const [composeTo, setComposeTo] = useState('');
  const [composeCC, setComposeCC] = useState('');
  const [composeBCC, setComposeBCC] = useState('');
  const [composeSubject, setComposeSubject] = useState('');
  const [composeBody, setComposeBody] = useState('');
  const [pendingMessages, setPendingMessages] = useState<PendingMessage[]>([]);
  const [ignoredMessageIds, setIgnoredMessageIds] = useState<Set<number>>(new Set());
  const [runningAnalysis, setRunningAnalysis] = useState(false);
  const [showPromptPreview, setShowPromptPreview] = useState(false);
  const [promptPreview, setPromptPreview] = useState<{system_prompt: string, user_prompt: string} | null>(null);
  const [statuses, setStatuses] = useState<CustomStatus[]>([]);
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [composeAttachments, setComposeAttachments] = useState<File[]>([]);
  const [lightboxImage, setLightboxImage] = useState<Attachment | null>(null);
  const [expandedTextAttachments, setExpandedTextAttachments] = useState<Set<number>>(new Set());
  const [imageBlobUrls, setImageBlobUrls] = useState<Map<number, string>>(new Map());
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [auditLogsExpanded, setAuditLogsExpanded] = useState(false);
  const [loadingAuditLogs, setLoadingAuditLogs] = useState(false);
  const [editingMessageId, setEditingMessageId] = useState<number | null>(null);
  const [editedMessageBody, setEditedMessageBody] = useState('');
  const [editedMessageSubject, setEditedMessageSubject] = useState('');
  const [editedMessageAttachments, setEditedMessageAttachments] = useState<File[]>([]);
  const [processingMessage, setProcessingMessage] = useState(false);
  const [showRejectDialog, setShowRejectDialog] = useState<number | null>(null);
  const [rejectionReason, setRejectionReason] = useState('');
  const [attachmentsExpanded, setAttachmentsExpanded] = useState(false);
  const [aiDecisionsExpanded, setAiDecisionsExpanded] = useState(false);
  const [checkingTracking, setCheckingTracking] = useState(false);
  const [trackingResult, setTrackingResult] = useState<any>(null);

  const stripHtml = (html: string): string => {
    // Remove HTML tags and decode entities
    const tmp = document.createElement('DIV');
    tmp.innerHTML = html;
    const text = tmp.textContent || tmp.innerText || '';
    // Clean up excessive whitespace
    return text.replace(/\s+/g, ' ').trim();
  };

  const loadPendingMessages = async () => {
    if (!ticket) return;
    try {
      const messages = await messagesApi.getPendingMessages({
        status: 'pending',
      });
      // Filter messages for this ticket
      setPendingMessages(messages.filter(msg => msg.ticket_number === ticket.ticket_number));
    } catch (err) {
      console.error('Failed to load pending messages:', err);
    }
  };

  const loadAttachments = async () => {
    if (!ticketNumber) return;
    try {
      const data = await ticketsApi.getAttachments(ticketNumber);
      setAttachments(data);

      // Load image blob URLs for thumbnails
      const newBlobUrls = new Map<number, string>();
      for (const attachment of data) {
        if (attachment.mime_type?.startsWith('image/')) {
          try {
            const blob = await client.get(`/api/attachments/${attachment.id}/view`, {
              responseType: 'blob',
            });
            const url = window.URL.createObjectURL(blob.data);
            newBlobUrls.set(attachment.id, url);
          } catch (err) {
            console.error(`Failed to load image thumbnail for attachment ${attachment.id}:`, err);
          }
        }
      }
      setImageBlobUrls(newBlobUrls);
    } catch (err) {
      console.error('Failed to load attachments:', err);
    }
  };

  const loadAuditLogs = async () => {
    if (!ticketNumber) return;
    setLoadingAuditLogs(true);
    try {
      const response = await client.get(`/api/tickets/${ticketNumber}/audit-logs`);
      setAuditLogs(response.data);
    } catch (err) {
      console.error('Failed to load audit logs:', err);
    } finally {
      setLoadingAuditLogs(false);
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Validate file type
      const allowedExtensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.tiff', '.tif', '.bmp', '.webp', '.docx', '.txt', '.csv', '.xlsx', '.xls'];
      const fileName = file.name.toLowerCase();
      const fileExt = fileName.substring(fileName.lastIndexOf('.'));

      if (!allowedExtensions.includes(fileExt)) {
        setReprocessMessage({
          type: 'error',
          text: `File type '${fileExt}' not allowed. Allowed types: PDF, images (JPG, PNG, GIF, TIFF, BMP, WebP), documents (DOCX, TXT, CSV, XLSX)`
        });
        setTimeout(() => setReprocessMessage(null), 5000);
        event.target.value = ''; // Reset input
        return;
      }

      // Check for dangerous file types
      const dangerousExtensions = ['.exe', '.bat', '.sh', '.cmd', '.com', '.scr', '.vbs', '.js', '.jar', '.app', '.dmg', '.msi'];
      if (dangerousExtensions.includes(fileExt)) {
        setReprocessMessage({
          type: 'error',
          text: 'Executable files are not allowed for security reasons'
        });
        setTimeout(() => setReprocessMessage(null), 5000);
        event.target.value = ''; // Reset input
        return;
      }

      // Check file size (100MB)
      const maxSize = 100 * 1024 * 1024;
      if (file.size > maxSize) {
        setReprocessMessage({
          type: 'error',
          text: 'File size exceeds 100MB limit'
        });
        setTimeout(() => setReprocessMessage(null), 5000);
        event.target.value = ''; // Reset input
        return;
      }

      setSelectedFile(file);
    }
  };

  const handleUploadAttachment = async () => {
    if (!selectedFile || !ticketNumber) return;

    setUploadingFile(true);
    try {
      await ticketsApi.uploadAttachment(ticketNumber, selectedFile);
      setSelectedFile(null);
      // Reset file input
      const fileInput = document.getElementById('file-upload') as HTMLInputElement;
      if (fileInput) fileInput.value = '';
      // Reload attachments
      await loadAttachments();
      setReprocessMessage({ type: 'success', text: 'Attachment uploaded successfully!' });
      setTimeout(() => setReprocessMessage(null), 3000);
    } catch (err: any) {
      setReprocessMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to upload attachment' });
    } finally {
      setUploadingFile(false);
    }
  };

  const handleDownloadAttachment = async (attachment: Attachment) => {
    try {
      const blob = await ticketsApi.downloadAttachment(attachment.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = attachment.original_filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setReprocessMessage({ type: 'error', text: 'Failed to download attachment' });
    }
  };

  const handleDeleteAttachment = async (attachmentId: number) => {
    if (!confirm('Are you sure you want to delete this attachment?')) return;

    try {
      await ticketsApi.deleteAttachment(attachmentId);
      await loadAttachments();
      setReprocessMessage({ type: 'success', text: 'Attachment deleted successfully!' });
      setTimeout(() => setReprocessMessage(null), 3000);
    } catch (err: any) {
      setReprocessMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to delete attachment' });
    }
  };

  const handleViewImage = (attachment: Attachment) => {
    if (attachment.mime_type?.startsWith('image/')) {
      setLightboxImage(attachment);
    }
  };

  const toggleExtractedText = (attachmentId: number) => {
    setExpandedTextAttachments(prev => {
      const newSet = new Set(prev);
      if (newSet.has(attachmentId)) {
        newSet.delete(attachmentId);
      } else {
        newSet.add(attachmentId);
      }
      return newSet;
    });
  };

  const isImageFile = (mimeType: string | null): boolean => {
    return mimeType?.startsWith('image/') || false;
  };

  const formatFileSize = (bytes: number | null): string => {
    if (!bytes) return 'Unknown size';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const handleComposeFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files) {
      const allowedExtensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.tiff', '.tif', '.bmp', '.webp', '.docx', '.txt', '.csv', '.xlsx', '.xls'];
      const dangerousExtensions = ['.exe', '.bat', '.sh', '.cmd', '.com', '.scr', '.vbs', '.js', '.jar', '.app', '.dmg', '.msi'];
      const maxSize = 100 * 1024 * 1024;
      const validFiles: File[] = [];
      const errors: string[] = [];

      Array.from(files).forEach((file) => {
        const fileName = file.name.toLowerCase();
        const fileExt = fileName.substring(fileName.lastIndexOf('.'));

        // Check for dangerous types
        if (dangerousExtensions.includes(fileExt)) {
          errors.push(`${file.name}: Executable files not allowed`);
          return;
        }

        // Check allowed types
        if (!allowedExtensions.includes(fileExt)) {
          errors.push(`${file.name}: File type '${fileExt}' not allowed`);
          return;
        }

        // Check file size
        if (file.size > maxSize) {
          errors.push(`${file.name}: Exceeds 100MB limit`);
          return;
        }

        validFiles.push(file);
      });

      if (errors.length > 0) {
        setReprocessMessage({
          type: 'error',
          text: errors.join('; ')
        });
        setTimeout(() => setReprocessMessage(null), 7000);
      }

      if (validFiles.length > 0) {
        setComposeAttachments(prev => [...prev, ...validFiles]);
      }

      event.target.value = ''; // Reset input
    }
  };

  const removeComposeAttachment = (index: number) => {
    setComposeAttachments(prev => prev.filter((_, i) => i !== index));
  };

  const handleEditedMessageFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files) {
      const allowedExtensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.tiff', '.tif', '.bmp', '.webp', '.docx', '.txt', '.csv', '.xlsx', '.xls'];
      const dangerousExtensions = ['.exe', '.bat', '.sh', '.cmd', '.com', '.scr', '.vbs', '.js', '.jar', '.app', '.dmg', '.msi'];
      const maxSize = 100 * 1024 * 1024;
      const validFiles: File[] = [];
      const errors: string[] = [];

      Array.from(files).forEach((file) => {
        const fileName = file.name.toLowerCase();
        const fileExt = fileName.substring(fileName.lastIndexOf('.'));

        // Check for dangerous types
        if (dangerousExtensions.includes(fileExt)) {
          errors.push(`${file.name}: Executable files not allowed`);
          return;
        }

        // Check allowed types
        if (!allowedExtensions.includes(fileExt)) {
          errors.push(`${file.name}: File type '${fileExt}' not allowed`);
          return;
        }

        // Check file size
        if (file.size > maxSize) {
          errors.push(`${file.name}: Exceeds 100MB limit`);
          return;
        }

        validFiles.push(file);
      });

      if (errors.length > 0) {
        alert('Some files were rejected:\n' + errors.join('\n'));
      }

      if (validFiles.length > 0) {
        setEditedMessageAttachments(prev => [...prev, ...validFiles]);
      }

      // Reset input
      event.target.value = '';
    }
  };

  const removeEditedMessageAttachment = (index: number) => {
    setEditedMessageAttachments(prev => prev.filter((_, i) => i !== index));
  };

  const handleComposeMessage = (recipientType: 'customer' | 'supplier' | 'internal') => {
    setComposeRecipientType(recipientType);
    setComposeExpanded(true);
    // Set default recipient based on type
    if (ticket) {
      if (recipientType === 'internal') {
        setComposeTo('');
        setComposeSubject('Internal note');
      } else {
        const defaultEmail = recipientType === 'customer'
          ? ticket.customer_email
          : (ticket.supplier_email || '');
        setComposeTo(defaultEmail);
        setComposeSubject(`Re: Ticket ${ticket.ticket_number}`);
      }
    }
  };

  const handleSendViaGmail = async () => {
    if (!ticket) return;

    setReprocessing(true);
    setReprocessMessage(null);

    try {
      if (composeRecipientType === 'internal') {
        // Save internal note
        await client.post(`/api/tickets/${ticket.ticket_number}/internal-note`, {
          subject: composeSubject,
          body: composeBody
        });

        // Upload attachments if any
        if (composeAttachments.length > 0) {
          for (const file of composeAttachments) {
            await ticketsApi.uploadAttachment(ticket.ticket_number, file);
          }
        }

        setReprocessMessage({ type: 'success', text: 'Internal note saved!' });
      } else {
        // Parse CC and BCC fields (comma-separated)
        const ccList = composeCC ? composeCC.split(',').map(e => e.trim()).filter(e => e) : [];
        const bccList = composeBCC ? composeBCC.split(',').map(e => e.trim()).filter(e => e) : [];

        // Always use FormData (endpoint expects Form data)
        const formData = new FormData();
        formData.append('to', composeTo);
        formData.append('subject', composeSubject);
        formData.append('body', composeBody);
        if (ccList.length > 0) formData.append('cc', JSON.stringify(ccList));
        if (bccList.length > 0) formData.append('bcc', JSON.stringify(bccList));
        if (ticket.gmail_thread_id) formData.append('thread_id', ticket.gmail_thread_id);

        // Append all attachments if any
        composeAttachments.forEach((file) => {
          formData.append('attachments', file);
        });

        await client.post(`/api/tickets/${ticket.ticket_number}/send-email`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });

        setReprocessMessage({ type: 'success', text: 'Email sent successfully via Gmail!' });
      }

      // Reset form and collapse
      setComposeExpanded(false);
      setComposeTo('');
      setComposeCC('');
      setComposeBCC('');
      setComposeSubject('');
      setComposeBody('');
      setComposeAttachments([]);

      // Refresh ticket to show new message
      setTimeout(() => {
        loadTicket();
        loadAttachments();
        setReprocessMessage(null);
      }, 2000);
    } catch (err: any) {
      console.error('Failed to send:', err);
      setReprocessMessage({
        type: 'error',
        text: err.response?.data?.detail || 'Failed to send'
      });
    } finally {
      setReprocessing(false);
    }
  };

  const handleMessageSent = () => {
    loadPendingMessages();
  };

  const toggleMessageIgnore = (messageId: number) => {
    setIgnoredMessageIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(messageId)) {
        newSet.delete(messageId);
      } else {
        newSet.add(messageId);
      }
      return newSet;
    });
  };

  const handleRunAIAnalysis = async () => {
    if (!ticket) return;

    // First, get the prompt preview
    setRunningAnalysis(true);
    try {
      const response = await client.post(`/api/tickets/${ticket.ticket_number}/analyze`, {
        ignored_message_ids: Array.from(ignoredMessageIds),
        preview_only: true
      });

      setPromptPreview({
        system_prompt: response.data.system_prompt,
        user_prompt: response.data.user_prompt
      });
      setShowPromptPreview(true);
    } catch (err: any) {
      setReprocessMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to generate prompt preview' });
      setTimeout(() => setReprocessMessage(null), 5000);
    } finally {
      setRunningAnalysis(false);
    }
  };

  const handleConfirmAnalysis = async () => {
    if (!ticket) return;

    setShowPromptPreview(false);
    setRunningAnalysis(true);
    try {
      await client.post(`/api/tickets/${ticket.ticket_number}/analyze`, {
        ignored_message_ids: Array.from(ignoredMessageIds),
        preview_only: false
      });
      await loadTicket(); // Reload to show new AI decision
      setReprocessMessage({ type: 'success', text: 'AI analysis completed successfully' });
    } catch (err: any) {
      setReprocessMessage({ type: 'error', text: err.response?.data?.detail || 'AI analysis failed' });
    } finally {
      setRunningAnalysis(false);
      setTimeout(() => setReprocessMessage(null), 5000);
    }
  };

  const handleFeedback = async (decisionId: number, feedbackType: 'correct' | 'incorrect') => {
    if (feedbackType === 'incorrect') {
      setFeedbackDecisionId(decisionId);
      setFeedbackNotes('');
    } else {
      // For positive feedback, submit immediately
      try {
        await client.post(`/api/ai-decisions/${decisionId}/feedback`, {
          feedback: feedbackType,
          feedback_notes: ''
        });
        await loadTicket(); // Reload to show updated feedback
      } catch (err) {
        console.error('Failed to save feedback:', err);
      }
    }
  };

  const submitFeedbackNotes = async () => {
    if (!feedbackDecisionId) return;

    setSavingFeedback(true);
    try {
      await client.post(`/api/ai-decisions/${feedbackDecisionId}/feedback`, {
        feedback: 'incorrect',
        feedback_notes: feedbackNotes
      });
      await loadTicket(); // Reload to show updated feedback
      setFeedbackDecisionId(null);
      setFeedbackNotes('');
    } catch (err) {
      console.error('Failed to save feedback:', err);
    } finally {
      setSavingFeedback(false);
    }
  };

  useEffect(() => {
    loadTicketList();
    loadStatuses();
  }, []);

  useEffect(() => {
    if (ticketNumber) {
      loadTicket();
      updateCurrentIndex();
    }
  }, [ticketNumber, ticketList]);

  useEffect(() => {
    if (ticket) {
      loadPendingMessages();
      loadAttachments();
    }
  }, [ticket]);

  const loadTicketList = async () => {
    try {
      const tickets = await ticketsApi.getTickets({ limit: 100 });
      setTicketList(tickets);
    } catch (err) {
      console.error('Failed to load ticket list:', err);
    }
  };

  const loadStatuses = async () => {
    try {
      const response = await client.get('/api/statuses');
      setStatuses(response.data);
    } catch (err) {
      console.error('Failed to load statuses:', err);
    }
  };

  const handleStatusChange = async (statusId: number) => {
    if (!ticket) return;

    setUpdatingStatus(true);
    try {
      await client.patch(`/api/tickets/${ticket.ticket_number}/status`, null, {
        params: { status_id: statusId }
      });
      await loadTicket(); // Reload to show updated status
    } catch (err: any) {
      console.error('Failed to update status:', err);
      setReprocessMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to update status' });
      setTimeout(() => setReprocessMessage(null), 5000);
    } finally {
      setUpdatingStatus(false);
    }
  };

  const handleApproveMessage = async (messageId: number, withEdits: boolean) => {
    setProcessingMessage(true);
    try {
      let attachmentPaths: string[] = [];

      // Upload attachments if any
      if (editedMessageAttachments.length > 0 && ticket) {
        for (const file of editedMessageAttachments) {
          try {
            const attachment = await ticketsApi.uploadAttachment(ticket.ticket_number, file);
            attachmentPaths.push(attachment.file_path);
          } catch (err) {
            console.error('Failed to upload attachment:', file.name, err);
            alert(`Failed to upload attachment: ${file.name}`);
            setProcessingMessage(false);
            return;
          }
        }
      }

      const approval: any = {
        action: 'approve',
        updated_data: withEdits ? {
          body: editedMessageBody,
          subject: editedMessageSubject,
          attachments: attachmentPaths.length > 0 ? attachmentPaths : undefined,
        } : undefined
      };

      await messagesApi.approveMessage(messageId, approval);
      await loadPendingMessages();
      setEditingMessageId(null);
      setEditedMessageBody('');
      setEditedMessageSubject('');
      setEditedMessageAttachments([]);

      // Reload ticket to show updated message history
      await loadTicket();
    } catch (err: any) {
      console.error('Failed to approve message:', err);
      alert('Failed to approve message: ' + (err.message || 'Unknown error'));
    } finally {
      setProcessingMessage(false);
    }
  };

  const handleRejectMessage = async (messageId: number) => {
    setProcessingMessage(true);
    try {
      const approval = {
        action: 'reject',
        rejection_reason: rejectionReason
      };

      await messagesApi.approveMessage(messageId, approval);
      await loadPendingMessages();
      setShowRejectDialog(null);
      setRejectionReason('');
    } catch (err: any) {
      console.error('Failed to reject message:', err);
      alert('Failed to reject message: ' + (err.message || 'Unknown error'));
    } finally {
      setProcessingMessage(false);
    }
  };

  const updateCurrentIndex = () => {
    const index = ticketList.findIndex(t => t.ticket_number === ticketNumber);
    setCurrentIndex(index);
  };

  const navigateToPrevious = () => {
    if (currentIndex > 0) {
      navigate(`/tickets/${ticketList[currentIndex - 1].ticket_number}`);
    }
  };

  const navigateToNext = () => {
    if (currentIndex >= 0 && currentIndex < ticketList.length - 1) {
      navigate(`/tickets/${ticketList[currentIndex + 1].ticket_number}`);
    }
  };

  const loadTicket = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await ticketsApi.getTicketDetail(ticketNumber!);
      setTicket(data);
    } catch (err: any) {
      console.error('Failed to load ticket:', err);
      setError(err.response?.data?.detail || 'Failed to load ticket details');
    } finally {
      setLoading(false);
    }
  };

  const handleReprocess = async () => {
    if (!ticketNumber) return;

    setReprocessing(true);
    setReprocessMessage(null);

    try {
      const response = await client.post(`/api/tickets/${ticketNumber}/reprocess`);

      // Show success message
      const confidence = response.data.confidence ? (response.data.confidence * 100).toFixed(0) : 'N/A';
      const escalated = response.data.requires_escalation ? ' (Escalated)' : '';
      setReprocessMessage({
        type: 'success',
        text: `✓ Ticket reprocessed successfully! Confidence: ${confidence}%${escalated}. New AI decision added.`
      });

      // Reload ticket to show new decision - with a small delay to ensure backend is done
      setTimeout(async () => {
        await loadTicket();
      }, 500);

      // Clear message after 7 seconds
      setTimeout(() => setReprocessMessage(null), 7000);
    } catch (err: any) {
      console.error('Failed to reprocess ticket:', err);
      setReprocessMessage({
        type: 'error',
        text: `✗ ${err.response?.data?.detail || 'Failed to reprocess ticket'}`
      });
      setTimeout(() => setReprocessMessage(null), 7000);
    } finally {
      setReprocessing(false);
    }
  };

  const handleRefresh = async () => {
    if (!ticketNumber) return;

    setRefreshing(true);
    try {
      await ticketsApi.refreshTicket(ticketNumber);

      // Reload ticket to show updated data
      await loadTicket();

      setReprocessMessage({
        type: 'success',
        text: '✓ Ticket refreshed successfully'
      });

      // Clear message after 3 seconds
      setTimeout(() => setReprocessMessage(null), 3000);
    } catch (err: any) {
      console.error('Failed to refresh ticket:', err);
      setReprocessMessage({
        type: 'error',
        text: `✗ ${err.response?.data?.detail || 'Failed to refresh ticket'}`
      });
      setTimeout(() => setReprocessMessage(null), 5000);
    } finally {
      setRefreshing(false);
    }
  };

  const handleCheckTracking = async () => {
    if (!ticketNumber) return;

    setCheckingTracking(true);
    setTrackingResult(null);
    try {
      const response = await client.get(`/api/tickets/${ticketNumber}/check-tracking`);
      setTrackingResult(response.data);
    } catch (err: any) {
      console.error('Failed to check tracking:', err);
      setTrackingResult({
        success: false,
        error: err.response?.data?.detail || 'Failed to check tracking'
      });
    } finally {
      setCheckingTracking(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <button
          onClick={() => navigate('/tickets')}
          className="flex items-center gap-2 text-indigo-600 hover:text-indigo-800"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Tickets
        </button>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error}</p>
        </div>
      </div>
    );
  }

  if (!ticket) {
    return (
      <div className="space-y-6">
        <button
          onClick={() => navigate('/tickets')}
          className="flex items-center gap-2 text-indigo-600 hover:text-indigo-800"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Tickets
        </button>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-yellow-800">Ticket not found</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/tickets')}
            className="flex items-center gap-2 text-indigo-600 hover:text-indigo-800"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </button>

          {/* Navigation arrows */}
          {ticketList.length > 0 && (
            <div className="flex items-center gap-2 border-l pl-4">
              <button
                onClick={navigateToPrevious}
                disabled={currentIndex <= 0}
                className="p-2 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-gray-700"
                title="Previous ticket"
              >
                <ChevronLeft className="h-5 w-5 text-gray-900" />
              </button>
              <span className="text-sm text-gray-600 min-w-[60px] text-center font-medium">
                {currentIndex + 1} / {ticketList.length}
              </span>
              <button
                onClick={navigateToNext}
                disabled={currentIndex >= ticketList.length - 1}
                className="p-2 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-gray-700"
                title="Next ticket"
              >
                <ChevronRight className="h-5 w-5 text-gray-900" />
              </button>
            </div>
          )}

          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-3xl font-bold text-gray-900">
                Ticket #{ticket.ticket_number}
              </h1>
              {ticket.escalated && (
                <AlertTriangle className="h-6 w-6 text-red-500" />
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Refresh ticket data from ticketing system"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
          <button
            onClick={handleReprocess}
            disabled={reprocessing}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Re-run AI analysis on this ticket"
          >
            <RefreshCw className={`h-4 w-4 ${reprocessing ? 'animate-spin' : ''}`} />
            {reprocessing ? 'Reprocessing...' : 'Reprocess'}
          </button>
          <button
            onClick={handleCheckTracking}
            disabled={checkingTracking}
            className="flex items-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Check live tracking status"
          >
            <Truck className={`h-4 w-4 ${checkingTracking ? 'animate-pulse' : ''}`} />
            {checkingTracking ? 'Checking...' : 'Check Tracking'}
          </button>
        </div>
      </div>

      {/* Reprocess Message */}
      {reprocessMessage && (
        <div className={`p-4 rounded-lg ${reprocessMessage.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
          {reprocessMessage.text}
        </div>
      )}

      {/* Tracking Result */}
      {trackingResult && (
        <div className={`p-6 rounded-lg ${trackingResult.success ? 'bg-blue-50 border-2 border-blue-200' : 'bg-red-50 border-2 border-red-200'}`}>
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-3">
              <Truck className={`h-6 w-6 ${trackingResult.success ? 'text-blue-600' : 'text-red-600'}`} />
              <h3 className="text-lg font-semibold text-gray-900">Live Tracking Status</h3>
            </div>
            <button
              onClick={() => setTrackingResult(null)}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {trackingResult.success ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-600 mb-1">Carrier</p>
                  <p className="text-base font-medium text-gray-900">{trackingResult.carrier || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">Tracking Number</p>
                  <p className="text-base font-medium text-gray-900">{trackingResult.tracking_number || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">Current Status</p>
                  <p className="text-base font-semibold text-blue-700">{trackingResult.status_text || 'Unknown'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">Status Code</p>
                  <p className="text-base font-mono text-gray-700">{trackingResult.status || 'unknown'}</p>
                </div>
                {trackingResult.location && (
                  <div>
                    <p className="text-sm text-gray-600 mb-1">Current Location</p>
                    <p className="text-base font-medium text-gray-900">{trackingResult.location}</p>
                  </div>
                )}
                {trackingResult.estimated_delivery && (
                  <div>
                    <p className="text-sm text-gray-600 mb-1">Estimated Delivery</p>
                    <p className="text-base font-medium text-gray-900">{trackingResult.estimated_delivery}</p>
                  </div>
                )}
                {trackingResult.last_update && (
                  <div>
                    <p className="text-sm text-gray-600 mb-1">Last Update</p>
                    <p className="text-base text-gray-700">{new Date(trackingResult.last_update).toLocaleString()}</p>
                  </div>
                )}
              </div>
              {trackingResult.tracking_url && (
                <div className="mt-4 pt-4 border-t border-blue-200">
                  <a
                    href={trackingResult.tracking_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-800 underline text-sm"
                  >
                    View on carrier website →
                  </a>
                </div>
              )}
              {trackingResult.cached && (
                <div className="mt-2 text-xs text-gray-500 italic">
                  ℹ️ Result cached (checked within last 2 hours)
                </div>
              )}
            </div>
          ) : (
            <div className="text-red-800">
              <p className="font-medium mb-2">Unable to check tracking</p>
              <p className="text-sm">{trackingResult.error || 'Unknown error'}</p>
              {trackingResult.tracking_url && (
                <div className="mt-4">
                  <a
                    href={trackingResult.tracking_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-red-600 hover:text-red-800 underline text-sm"
                  >
                    Try checking on carrier website →
                  </a>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Ticket Information and Order Details - Side by Side */}
      <div className="grid grid-cols-2 gap-6">
        {/* Ticket Info Card */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Ticket Information</h2>
          <div className="space-y-3">
            <div>
              <p className="text-xs text-gray-500 mb-1">Status</p>
              <select
                value={ticket.custom_status_id || ''}
                onChange={(e) => handleStatusChange(parseInt(e.target.value))}
                disabled={updatingStatus}
                className={`w-full px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  ticket.custom_status
                    ? `bg-${ticket.custom_status.color}-100 text-${ticket.custom_status.color}-800 font-medium`
                    : 'bg-white text-gray-900'
                }`}
              >
                <option value="">No status set</option>
                {statuses.map((status) => (
                  <option key={status.id} value={status.id}>
                    {status.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <p className="text-xs text-gray-500">Customer Email</p>
              <p className="text-sm font-medium text-gray-900">{ticket.customer_email}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Created</p>
              <p className="text-sm font-medium text-gray-900">
                {formatInCET(ticket.created_at)}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Last Updated</p>
              <p className="text-sm font-medium text-gray-900">
                {formatInCET(ticket.last_updated)}
              </p>
            </div>
            {ticket.escalated && ticket.escalation_reason && (
              <>
                <div>
                  <p className="text-xs text-gray-500">Escalation Reason</p>
                  <p className="text-sm font-medium text-red-800">{ticket.escalation_reason}</p>
                </div>
                {ticket.escalation_date && (
                  <div>
                    <p className="text-xs text-gray-500">Escalation Date</p>
                    <p className="text-sm font-medium text-gray-900">
                      {formatInCET(ticket.escalation_date)}
                    </p>
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {/* Order Details */}
        {(ticket.order_date || ticket.product_details) && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Order Details</h2>
            <div className="space-y-3">
              {ticket.order_date && (
                <div>
                  <p className="text-xs text-gray-500">Order Date</p>
                  <p className="text-sm font-medium text-gray-900">{ticket.order_date}</p>
                </div>
              )}
              {ticket.expected_delivery_date && (
                <div>
                  <p className="text-xs text-gray-500">Expected Delivery</p>
                  <p className="text-sm font-medium text-gray-900">{ticket.expected_delivery_date}</p>
                </div>
              )}
              {ticket.product_details && (() => {
                try {
                  const products = JSON.parse(ticket.product_details);
                  return (
                    <div>
                      <p className="text-xs text-gray-500 mb-2">Products</p>
                      <div className="space-y-2">
                        {products.map((product: any, index: number) => (
                          <div key={index} className="border border-gray-200 rounded p-3">
                            <div className="flex justify-between items-start mb-1">
                              <p className="text-sm font-medium text-gray-900">{product.title || 'No title'}</p>
                              <p className="text-sm font-medium text-gray-900">Qty: {product.quantity || 1}</p>
                            </div>
                            <div className="flex justify-between items-center">
                              <p className="text-xs text-gray-500">SKU: {product.sku || 'N/A'}</p>
                              {product.price && <p className="text-xs text-gray-500">€{product.price.toFixed(2)}</p>}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                } catch (e) {
                  return <p className="text-sm text-red-600">Error parsing product details</p>;
                }
              })()}
            </div>
          </div>
        )}
      </div>

      {/* Customer and Supplier Information - Side by Side */}
      <div className="grid grid-cols-2 gap-6">
        {/* Customer Information */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Customer Information</h2>
          <div className="space-y-3">
            {ticket.order_number && (
              <div>
                <p className="text-xs text-gray-500">Amazon Order Number</p>
                <a
                  href={`https://sellercentral.amazon.de/orders-v3/order/${ticket.order_number}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-medium text-blue-600 hover:text-blue-800 underline"
                >
                  {ticket.order_number}
                </a>
              </div>
            )}
            {ticket.customer_name && (
              <div>
                <p className="text-sm font-medium text-gray-900">{ticket.customer_name}</p>
              </div>
            )}
            {ticket.customer_address && (
              <div>
                <p className="text-sm font-medium text-gray-900">
                  {ticket.customer_address}
                  {ticket.customer_city && <><br />{ticket.customer_postal_code} {ticket.customer_city}</>}
                  {ticket.customer_country && <><br />{ticket.customer_country}</>}
                </p>
              </div>
            )}
            {ticket.customer_phone && (
              <div>
                <p className="text-sm font-medium text-gray-900">{ticket.customer_phone}</p>
              </div>
            )}
          </div>
        </div>

        {/* Supplier Information */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Supplier Information</h2>
          <div className="space-y-3">
            {ticket.purchase_order_number && (
              <div>
                <p className="text-sm font-medium text-gray-900">PO#: {ticket.purchase_order_number}</p>
              </div>
            )}
            {ticket.supplier_name && (
              <div>
                <p className="text-sm font-medium text-gray-900">{ticket.supplier_name}</p>
              </div>
            )}
            {ticket.tracking_number && ticket.carrier_name && (
              <div>
                <p className="text-sm font-medium text-gray-900">
                  {ticket.carrier_name}:{' '}
                  {ticket.tracking_url ? (
                    <a
                      href={ticket.tracking_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 underline"
                    >
                      {ticket.tracking_number}
                    </a>
                  ) : (
                    ticket.tracking_number
                  )}
                </p>
              </div>
            )}
            {ticket.supplier_contact_person && (
              <div>
                <p className="text-xs text-gray-500">Contact Person</p>
                <p className="text-sm font-medium text-gray-900">{ticket.supplier_contact_person}</p>
              </div>
            )}
            {ticket.supplier_email && (
              <div>
                <p className="text-xs text-gray-500">Email</p>
                <p className="text-sm font-medium text-gray-900">{ticket.supplier_email}</p>
              </div>
            )}
            {ticket.supplier_phone && (
              <div>
                <p className="text-xs text-gray-500">Phone</p>
                <p className="text-sm font-medium text-gray-900">{ticket.supplier_phone}</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Message Composition */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b border-gray-200">
          <div className="flex gap-3 justify-center">
            <button
              onClick={() => handleComposeMessage('customer')}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
            >
              <Send className="h-4 w-4" />
              Send to Customer
            </button>
            <button
              onClick={() => handleComposeMessage('supplier')}
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
            >
              <Send className="h-4 w-4" />
              Send to Supplier
            </button>
            <button
              onClick={() => handleComposeMessage('internal')}
              className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
            >
              <Send className="h-4 w-4" />
              Internal note
            </button>
          </div>
        </div>

        {/* Expandable Compose Form */}
        {composeExpanded && (
          <div className="p-6 bg-gray-50 border-t border-gray-200">
            <div className="space-y-4">
              {/* Only show To/CC/BCC for emails, not internal notes */}
              {composeRecipientType !== 'internal' && (
                <>
                  {/* To Address */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      To
                    </label>
                    <input
                      type="email"
                      value={composeTo}
                      onChange={(e) => setComposeTo(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                      placeholder="recipient@example.com"
                    />
                  </div>

                  {/* CC */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      CC (comma-separated)
                    </label>
                    <input
                      type="text"
                      value={composeCC}
                      onChange={(e) => setComposeCC(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                      placeholder="email1@example.com, email2@example.com"
                    />
                  </div>

                  {/* BCC */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      BCC (comma-separated)
                    </label>
                    <input
                      type="text"
                      value={composeBCC}
                      onChange={(e) => setComposeBCC(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                      placeholder="email1@example.com, email2@example.com"
                    />
                  </div>
                </>
              )}

              {/* Subject */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Subject
                </label>
                <input
                  type="text"
                  value={composeSubject}
                  onChange={(e) => setComposeSubject(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  placeholder="Email subject"
                />
              </div>

              {/* Body */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Message
                </label>
                <textarea
                  value={composeBody}
                  onChange={(e) => setComposeBody(e.target.value)}
                  rows={8}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  placeholder="Type your message here..."
                />
              </div>

              {/* Attachments */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Attachments
                </label>
                <div className="space-y-2">
                  <input
                    type="file"
                    multiple
                    accept=".pdf,.jpg,.jpeg,.png,.tiff,.tif,.bmp,.docx,.txt,.csv,.xlsx,.xls"
                    onChange={handleComposeFileSelect}
                    className="block w-full text-sm text-gray-500
                      file:mr-4 file:py-2 file:px-4
                      file:rounded-lg file:border-0
                      file:text-sm file:font-semibold
                      file:bg-indigo-50 file:text-indigo-700
                      hover:file:bg-indigo-100"
                  />
                  {composeAttachments.length > 0 && (
                    <div className="space-y-1">
                      {composeAttachments.map((file, index) => (
                        <div key={index} className="flex items-center justify-between bg-gray-50 p-2 rounded">
                          <div className="flex items-center gap-2">
                            <Paperclip className="h-4 w-4 text-gray-400" />
                            <span className="text-sm text-gray-700">{file.name}</span>
                            <span className="text-xs text-gray-500">({formatFileSize(file.size)})</span>
                          </div>
                          <button
                            onClick={() => removeComposeAttachment(index)}
                            className="text-red-600 hover:text-red-800"
                          >
                            <XCircle className="h-4 w-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Info Note */}
              {composeRecipientType !== 'internal' && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <p className="text-sm text-blue-800">
                    <strong>Note:</strong> Email will be sent through Gmail API in the background and automatically threaded with the existing conversation.
                  </p>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-3">
                <button
                  onClick={handleSendViaGmail}
                  disabled={
                    composeRecipientType === 'internal'
                      ? (!composeSubject || !composeBody || reprocessing)
                      : (!composeTo || !composeSubject || !composeBody || reprocessing)
                  }
                  className="flex items-center gap-2 px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Send className="h-4 w-4" />
                  {reprocessing
                    ? (composeRecipientType === 'internal' ? 'Saving...' : 'Sending...')
                    : (composeRecipientType === 'internal' ? 'Save Note' : 'Send via Gmail')
                  }
                </button>
                <button
                  onClick={() => {
                    setComposeExpanded(false);
                    setComposeTo('');
                    setComposeCC('');
                    setComposeBCC('');
                    setComposeSubject('');
                    setComposeBody('');
                    setComposeAttachments([]);
                  }}
                  className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Pending Messages */}
      {pendingMessages.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            AI-Generated Messages Pending Approval
          </h2>
          <div className="space-y-4">
            {pendingMessages.map((msg) => (
              <div key={msg.id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-900">
                      To: {msg.message_type.charAt(0).toUpperCase() + msg.message_type.slice(1)}
                    </span>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      msg.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                      msg.status === 'sent' ? 'bg-green-100 text-green-800' :
                      msg.status === 'rejected' ? 'bg-red-100 text-red-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {msg.status}
                    </span>
                    {msg.confidence_score !== null && (
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        msg.confidence_score >= 0.8 ? 'bg-green-100 text-green-800' :
                        msg.confidence_score >= 0.6 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {(msg.confidence_score * 100).toFixed(0)}% confidence
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-gray-500">
                    {formatInCET(msg.created_at)}
                  </span>
                </div>

                {editingMessageId === msg.id ? (
                  // Edit mode
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Subject
                      </label>
                      <input
                        type="text"
                        value={editedMessageSubject}
                        onChange={(e) => setEditedMessageSubject(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Message Body
                      </label>
                      <textarea
                        value={editedMessageBody}
                        onChange={(e) => setEditedMessageBody(e.target.value)}
                        rows={8}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent font-mono text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Attachments
                      </label>
                      <div className="space-y-2">
                        <input
                          type="file"
                          multiple
                          accept=".pdf,.jpg,.jpeg,.png,.tiff,.tif,.bmp,.docx,.txt,.csv,.xlsx,.xls"
                          onChange={handleEditedMessageFileSelect}
                          className="block w-full text-sm text-gray-500
                            file:mr-4 file:py-2 file:px-4
                            file:rounded-lg file:border-0
                            file:text-sm file:font-semibold
                            file:bg-indigo-50 file:text-indigo-700
                            hover:file:bg-indigo-100"
                        />
                        {editedMessageAttachments.length > 0 && (
                          <div className="space-y-1">
                            {editedMessageAttachments.map((file, index) => (
                              <div key={index} className="flex items-center justify-between bg-gray-50 p-2 rounded">
                                <div className="flex items-center gap-2">
                                  <Paperclip className="h-4 w-4 text-gray-400" />
                                  <span className="text-sm text-gray-700">{file.name}</span>
                                  <span className="text-xs text-gray-500">({formatFileSize(file.size)})</span>
                                </div>
                                <button
                                  onClick={() => removeEditedMessageAttachment(index)}
                                  className="text-red-600 hover:text-red-800"
                                >
                                  <XCircle className="h-4 w-4" />
                                </button>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleApproveMessage(msg.id, true)}
                        disabled={processingMessage}
                        className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:bg-gray-400"
                      >
                        {processingMessage ? 'Saving...' : 'Save & Approve'}
                      </button>
                      <button
                        onClick={() => {
                          setEditingMessageId(null);
                          setEditedMessageBody('');
                          setEditedMessageSubject('');
                          setEditedMessageAttachments([]);
                        }}
                        disabled={processingMessage}
                        className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:bg-gray-300"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  // View mode
                  <div>
                    <p className="text-sm font-medium text-gray-900 mb-2">{msg.subject}</p>
                    <p className="text-sm text-gray-600 whitespace-pre-wrap mb-3">{msg.body}</p>

                    {msg.status === 'pending' && (
                      <div className="flex gap-2 mt-3 pt-3 border-t">
                        <button
                          onClick={() => handleApproveMessage(msg.id, false)}
                          disabled={processingMessage}
                          className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:bg-gray-400"
                        >
                          {processingMessage ? 'Processing...' : 'Approve & Send'}
                        </button>
                        <button
                          onClick={() => {
                            setEditingMessageId(msg.id);
                            setEditedMessageBody(msg.body);
                            setEditedMessageSubject(msg.subject || '');
                          }}
                          disabled={processingMessage}
                          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:bg-gray-400"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => setShowRejectDialog(msg.id)}
                          disabled={processingMessage}
                          className="px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 disabled:bg-gray-400"
                        >
                          Reject
                        </button>
                      </div>
                    )}

                    {msg.status === 'sent' && msg.sent_at && (
                      <p className="text-xs text-green-600 mt-2">
                        Sent at {formatInCET(msg.sent_at)}
                      </p>
                    )}

                    {msg.status === 'rejected' && msg.rejection_reason && (
                      <div className="mt-2 p-2 bg-red-50 rounded">
                        <p className="text-xs text-red-600">
                          <strong>Rejection reason:</strong> {msg.rejection_reason}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Reject Dialog */}
      {showRejectDialog !== null && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Reject Message
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              Please provide a reason for rejecting this message:
            </p>
            <textarea
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              rows={4}
              placeholder="Reason for rejection..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent mb-4"
            />
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => {
                  setShowRejectDialog(null);
                  setRejectionReason('');
                }}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={() => handleRejectMessage(showRejectDialog)}
                disabled={!rejectionReason.trim() || processingMessage}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-gray-400"
              >
                {processingMessage ? 'Rejecting...' : 'Confirm Rejection'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Ticket Message History */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Message History ({ticket.messages?.length || 0})
          </h2>
          {ticket.status === 'imported' && (
            <button
              onClick={handleRunAIAnalysis}
              disabled={runningAnalysis}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <RefreshCw className={`h-4 w-4 ${runningAnalysis ? 'animate-spin' : ''}`} />
              {runningAnalysis ? 'Analyzing...' : 'Run AI Analysis'}
            </button>
          )}
        </div>
        <div className="space-y-3">
          {!ticket.messages || ticket.messages.length === 0 ? (
            <p className="text-gray-500 text-sm">No messages found for this ticket.</p>
          ) : (
            ticket.messages.map((message) => {
              const isSupplierMessage = message.messageType === 'supplier' || message.messageType === 'operator_to_supplier';

              const isIgnored = ignoredMessageIds.has(message.id);

              return (
                <div
                  key={message.id}
                  className={`border rounded-lg p-4 ${
                    isIgnored
                      ? 'border-gray-300 bg-gray-100 opacity-60'
                      : message.isInternal
                      ? 'border-yellow-200 bg-yellow-50'
                      : isSupplierMessage
                      ? 'border-orange-200 bg-orange-50'
                      : 'border-gray-200 bg-white'
                  }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    {ticket.status === 'imported' && (
                      <input
                        type="checkbox"
                        checked={isIgnored}
                        onChange={() => toggleMessageIgnore(message.id)}
                        className="mt-1 mr-3 h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                        title="Ignore this message in AI analysis"
                      />
                    )}
                    <div className="flex items-center gap-2">
                      {message.isInternal ? (
                        <Lock className="h-4 w-4 text-yellow-600" />
                      ) : (
                        <User className="h-4 w-4 text-gray-600" />
                      )}
                      <div>
                        <span className="text-sm font-medium text-gray-900">
                          {message.authorName || message.authorEmail || 'Unknown'}
                        </span>
                        {message.isInternal && (
                          <span className="ml-2 text-xs text-yellow-700 font-medium">Internal Note</span>
                        )}
                        {isSupplierMessage && (
                          <span className="ml-2 text-xs text-orange-700 font-medium">Supplier</span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-500">
                        {formatInCET(message.createdAt)}
                      </span>
                      {message.messageType && (
                        <span className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600">
                          {message.messageType}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="text-sm text-gray-700 pl-6">
                    {stripHtml(message.messageText)}
                  </div>

                  {/* Attachments for this message */}
                  {message.gmail_message_id && attachments.some(att => att.gmail_message_id === message.gmail_message_id) && (
                    <div className="mt-3 pl-6 space-y-2">
                      {attachments
                        .filter(att => att.gmail_message_id === message.gmail_message_id)
                        .map(attachment => (
                          <div
                            key={attachment.id}
                            className="border rounded p-2 bg-gray-50 hover:bg-gray-100"
                          >
                            <div className="flex items-start gap-2">
                              {/* Thumbnail for images */}
                              {isImageFile(attachment.mime_type) && imageBlobUrls.has(attachment.id) ? (
                                <div className="flex-shrink-0">
                                  <img
                                    src={imageBlobUrls.get(attachment.id)}
                                    alt={attachment.original_filename}
                                    className="w-12 h-12 object-cover rounded border cursor-pointer hover:opacity-80"
                                    onClick={() => handleViewImage(attachment)}
                                  />
                                </div>
                              ) : (
                                <Paperclip className="h-4 w-4 text-gray-400 mt-0.5 flex-shrink-0" />
                              )}

                              <div className="flex-1 min-w-0">
                                <p className="text-xs font-medium text-gray-900 truncate">
                                  {attachment.original_filename}
                                </p>
                                <div className="flex items-center gap-2 text-xs text-gray-500">
                                  <span>{formatFileSize(attachment.file_size)}</span>
                                  {attachment.extraction_status === 'completed' && (
                                    <span className="text-green-600">✓ Text extracted</span>
                                  )}
                                </div>

                                {/* Extracted Text */}
                                {attachment.extracted_text && attachment.extraction_status === 'completed' && (
                                  <div className="mt-1">
                                    <button
                                      onClick={() => toggleExtractedText(attachment.id)}
                                      className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700"
                                    >
                                      {expandedTextAttachments.has(attachment.id) ? (
                                        <>
                                          <ChevronUp className="h-3 w-3" />
                                          Hide text
                                        </>
                                      ) : (
                                        <>
                                          <ChevronDown className="h-3 w-3" />
                                          Show text
                                        </>
                                      )}
                                    </button>
                                    {expandedTextAttachments.has(attachment.id) && (
                                      <div className="mt-1 p-2 bg-white rounded text-xs text-gray-700 max-h-32 overflow-y-auto whitespace-pre-wrap border">
                                        {attachment.extracted_text}
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>

                              <div className="flex items-center gap-1 flex-shrink-0">
                                {isImageFile(attachment.mime_type) && (
                                  <button
                                    onClick={() => handleViewImage(attachment)}
                                    className="p-1 text-purple-600 hover:bg-purple-50 rounded"
                                    title="View image"
                                  >
                                    <Eye className="h-3 w-3" />
                                  </button>
                                )}
                                <button
                                  onClick={() => handleDownloadAttachment(attachment)}
                                  className="p-1 text-blue-600 hover:bg-blue-50 rounded"
                                  title="Download"
                                >
                                  <Download className="h-3 w-3" />
                                </button>
                              </div>
                            </div>
                          </div>
                        ))}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Attachments Overview & Upload */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Paperclip className="h-5 w-5" />
            Manual Upload & Attachments Overview ({attachments.length})
          </h2>
          <button
            onClick={() => setAttachmentsExpanded(!attachmentsExpanded)}
            className="text-gray-500 hover:text-gray-700 transition-colors"
          >
            {attachmentsExpanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
          </button>
        </div>
        {attachmentsExpanded && (
          <>
        <p className="text-xs text-gray-500 mb-4">
          Upload files manually here. Email attachments are shown inline with their respective messages above.
        </p>

        {/* Upload Section */}
        <div className="mb-4 p-4 bg-gray-50 rounded-lg">
          <div className="flex items-center gap-3">
            <label className="flex-1">
              <input
                type="file"
                id="file-upload"
                accept=".pdf,.jpg,.jpeg,.png,.tiff,.tif,.bmp,.docx,.txt,.csv,.xlsx,.xls"
                onChange={handleFileSelect}
                className="block w-full text-sm text-gray-500
                  file:mr-4 file:py-2 file:px-4
                  file:rounded-lg file:border-0
                  file:text-sm file:font-semibold
                  file:bg-blue-50 file:text-blue-700
                  hover:file:bg-blue-100"
              />
            </label>
            {selectedFile && (
              <button
                onClick={handleUploadAttachment}
                disabled={uploadingFile}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <Upload className={`h-4 w-4 ${uploadingFile ? 'animate-pulse' : ''}`} />
                {uploadingFile ? 'Uploading...' : 'Upload'}
              </button>
            )}
          </div>
          <p className="text-xs text-gray-500 mt-2">
            Supported formats: PDF, Images (JPG, PNG, TIFF, BMP), Word (DOCX), Excel (XLSX, XLS), Text (TXT, CSV). Max size: 10MB
          </p>
        </div>

        {/* Attachments List */}
        <div className="space-y-3">
          {attachments.length === 0 ? (
            <p className="text-gray-500 text-sm">No attachments for this ticket.</p>
          ) : (
            attachments.map((attachment) => (
              <div
                key={attachment.id}
                className="border rounded-lg p-3 hover:bg-gray-50"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    {/* Thumbnail for images */}
                    {isImageFile(attachment.mime_type) ? (
                      <div className="flex-shrink-0">
                        {imageBlobUrls.has(attachment.id) ? (
                          <img
                            src={imageBlobUrls.get(attachment.id)}
                            alt={attachment.original_filename}
                            className="w-16 h-16 object-cover rounded border cursor-pointer hover:opacity-80"
                            onClick={() => handleViewImage(attachment)}
                          />
                        ) : (
                          <div className="w-16 h-16 bg-gray-100 rounded border flex items-center justify-center">
                            <Paperclip className="h-6 w-6 text-gray-400" />
                          </div>
                        )}
                      </div>
                    ) : (
                      <Paperclip className="h-4 w-4 text-gray-400 mt-1 flex-shrink-0" />
                    )}

                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {attachment.original_filename}
                      </p>
                      <div className="flex items-center gap-3 text-xs text-gray-500 flex-wrap">
                        <span>{formatFileSize(attachment.file_size)}</span>
                        <span>{attachment.mime_type || 'Unknown type'}</span>
                        <span>{formatInCET(attachment.created_at)}</span>
                        {attachment.extraction_status === 'completed' && (
                          <span className="text-green-600">✓ Text extracted</span>
                        )}
                      </div>

                      {/* Extracted Text Section */}
                      {attachment.extracted_text && attachment.extraction_status === 'completed' && (
                        <div className="mt-2">
                          <button
                            onClick={() => toggleExtractedText(attachment.id)}
                            className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700"
                          >
                            {expandedTextAttachments.has(attachment.id) ? (
                              <>
                                <ChevronUp className="h-3 w-3" />
                                Hide extracted text
                              </>
                            ) : (
                              <>
                                <ChevronDown className="h-3 w-3" />
                                Show extracted text
                              </>
                            )}
                          </button>
                          {expandedTextAttachments.has(attachment.id) && (
                            <div className="mt-2 p-2 bg-gray-50 rounded text-xs text-gray-700 max-h-48 overflow-y-auto whitespace-pre-wrap">
                              {attachment.extracted_text}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-1 flex-shrink-0">
                    {isImageFile(attachment.mime_type) && (
                      <button
                        onClick={() => handleViewImage(attachment)}
                        className="p-2 text-purple-600 hover:bg-purple-50 rounded"
                        title="View image"
                      >
                        <Eye className="h-4 w-4" />
                      </button>
                    )}
                    <button
                      onClick={() => handleDownloadAttachment(attachment)}
                      className="p-2 text-blue-600 hover:bg-blue-50 rounded"
                      title="Download"
                    >
                      <Download className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDeleteAttachment(attachment.id)}
                      className="p-2 text-red-600 hover:bg-red-50 rounded"
                      title="Delete"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
          </>
        )}
      </div>

      {/* AI Decisions */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">
            AI Decisions ({ticket.ai_decisions.length})
          </h2>
          <button
            onClick={() => setAiDecisionsExpanded(!aiDecisionsExpanded)}
            className="text-gray-500 hover:text-gray-700 transition-colors"
          >
            {aiDecisionsExpanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
          </button>
        </div>
        {aiDecisionsExpanded && (
        <div className="space-y-4">
          {ticket.ai_decisions.length === 0 ? (
            <p className="text-gray-500 text-sm">No AI decisions recorded for this ticket.</p>
          ) : (
            ticket.ai_decisions.map((decision) => (
              <div
                key={decision.id}
                className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-gray-400" />
                    <span className="text-sm font-medium text-gray-900">
                      {formatInCET(decision.timestamp)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {decision.feedback ? (
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                          decision.feedback === 'correct'
                            ? 'bg-green-100 text-green-800'
                            : decision.feedback === 'incorrect'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-yellow-100 text-yellow-800'
                        }`}
                      >
                        {decision.feedback === 'correct' && <CheckCircle className="h-3 w-3 mr-1" />}
                        {decision.feedback === 'incorrect' && <XCircle className="h-3 w-3 mr-1" />}
                        {decision.feedback}
                      </span>
                    ) : (
                      <div className="flex gap-1">
                        <button
                          onClick={() => handleFeedback(decision.id, 'correct')}
                          className="p-1 hover:bg-green-50 rounded text-green-600 hover:text-green-700"
                          title="Mark as correct"
                        >
                          <ThumbsUp className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleFeedback(decision.id, 'incorrect')}
                          className="p-1 hover:bg-red-50 rounded text-red-600 hover:text-red-700"
                          title="Mark as incorrect and add notes"
                        >
                          <ThumbsDown className="h-4 w-4" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 mb-3">
                  {decision.detected_language && (
                    <div>
                      <p className="text-xs text-gray-500">Language</p>
                      <p className="text-sm font-medium text-gray-900">{decision.detected_language}</p>
                    </div>
                  )}
                  {decision.detected_intent && (
                    <div>
                      <p className="text-xs text-gray-500">Intent</p>
                      <p className="text-sm font-medium text-gray-900">{decision.detected_intent}</p>
                    </div>
                  )}
                  {decision.confidence_score !== null && (
                    <div>
                      <p className="text-xs text-gray-500">Confidence</p>
                      <p className="text-sm font-medium text-gray-900">
                        {(decision.confidence_score * 100).toFixed(1)}%
                      </p>
                    </div>
                  )}
                  <div>
                    <p className="text-xs text-gray-500">Action Taken</p>
                    <p className="text-sm font-medium text-gray-900">{decision.action_taken}</p>
                  </div>
                </div>

                {decision.recommended_action && (
                  <div className="mb-3">
                    <p className="text-xs text-gray-500 mb-1">Recommended Action</p>
                    <p className="text-sm text-gray-700">{decision.recommended_action}</p>
                  </div>
                )}

                {decision.response_generated && (
                  <div className="mb-3">
                    <p className="text-xs text-gray-500 mb-1">Generated Response</p>
                    <div className="bg-gray-50 rounded p-3 text-sm text-gray-700 whitespace-pre-wrap">
                      {decision.response_generated}
                    </div>
                  </div>
                )}

                {decision.feedback_notes && (
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Feedback Notes</p>
                    <p className="text-sm text-gray-700 italic">{decision.feedback_notes}</p>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
        )}
      </div>

      {/* Audit Log Section */}
      <div className="bg-white rounded-lg shadow">
        <button
          onClick={() => {
            setAuditLogsExpanded(!auditLogsExpanded);
            if (!auditLogsExpanded && auditLogs.length === 0) {
              loadAuditLogs();
            }
          }}
          className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-gray-50 transition-colors"
        >
          <div className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-gray-500" />
            <h2 className="text-lg font-semibold text-gray-900">Activity Log</h2>
            <span className="text-sm text-gray-500">({auditLogs.length} entries)</span>
          </div>
          {auditLogsExpanded ? (
            <ChevronUp className="h-5 w-5 text-gray-500" />
          ) : (
            <ChevronDown className="h-5 w-5 text-gray-500" />
          )}
        </button>

        {auditLogsExpanded && (
          <div className="border-t border-gray-200 px-6 py-4">
            {loadingAuditLogs ? (
              <div className="text-center py-8 text-gray-500">
                Loading activity log...
              </div>
            ) : auditLogs.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No activity recorded yet
              </div>
            ) : (
              <div className="space-y-3">
                {auditLogs.map((log: any) => (
                  <div key={log.id} className="flex gap-4 border-b border-gray-100 pb-3 last:border-0">
                    <div className="flex-shrink-0 w-32 text-xs text-gray-500">
                      {formatInCET(log.created_at)}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-start gap-2">
                        <User className="h-4 w-4 text-gray-400 mt-0.5 flex-shrink-0" />
                        <div className="flex-1">
                          <div className="text-sm">
                            <span className="font-medium text-gray-700">{log.username}</span>
                            <span className="text-gray-600"> {log.action_description}</span>
                          </div>
                          {log.field_name && (
                            <div className="mt-1 text-xs text-gray-500">
                              <span className="font-medium">{log.field_name}:</span>
                              {log.old_value && (
                                <span className="ml-1">
                                  <span className="line-through text-red-600">{log.old_value}</span>
                                  {' → '}
                                </span>
                              )}
                              {log.new_value && (
                                <span className="text-green-600">{log.new_value}</span>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Feedback Notes Modal */}
      {feedbackDecisionId && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-lg w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">What went wrong?</h3>
            <p className="text-sm text-gray-600 mb-4">
              Please describe what the AI did incorrectly. This feedback will be used to improve the system prompt.
            </p>
            <textarea
              value={feedbackNotes}
              onChange={(e) => setFeedbackNotes(e.target.value)}
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-gray-900 mb-4"
              placeholder="Example: You did not respond in the customer's language (German). Always respond in the same language as the customer's message."
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  setFeedbackDecisionId(null);
                  setFeedbackNotes('');
                }}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-md"
              >
                Cancel
              </button>
              <button
                onClick={submitFeedbackNotes}
                disabled={!feedbackNotes.trim() || savingFeedback}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {savingFeedback ? 'Saving...' : 'Submit Feedback'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Prompt Preview Modal */}
      {showPromptPreview && promptPreview && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">AI Analysis Prompt Preview</h2>
              <p className="text-sm text-gray-600 mt-1">Review the prompt that will be sent to the LLM</p>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">System Prompt</h3>
                <div className="bg-gray-50 border border-gray-200 rounded p-4">
                  <pre className="text-xs text-gray-800 whitespace-pre-wrap font-mono">{promptPreview.system_prompt}</pre>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">User Prompt (Ticket Data)</h3>
                <div className="bg-blue-50 border border-blue-200 rounded p-4">
                  <pre className="text-xs text-gray-800 whitespace-pre-wrap font-mono">{promptPreview.user_prompt}</pre>
                </div>
              </div>
            </div>

            <div className="p-6 border-t border-gray-200 flex gap-3 justify-end">
              <button
                onClick={() => setShowPromptPreview(false)}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmAnalysis}
                disabled={runningAnalysis}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <RefreshCw className={`h-4 w-4 ${runningAnalysis ? 'animate-spin' : ''}`} />
                {runningAnalysis ? 'Running Analysis...' : 'Confirm & Run Analysis'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Image Lightbox Modal */}
      {lightboxImage && (
        <div
          className="fixed inset-0 bg-black bg-opacity-90 flex items-center justify-center z-50 p-4"
          onClick={() => setLightboxImage(null)}
        >
          <button
            onClick={() => setLightboxImage(null)}
            className="absolute top-4 right-4 p-2 bg-white rounded-full hover:bg-gray-100 shadow-lg"
            title="Close"
          >
            <X className="h-6 w-6 text-gray-700" />
          </button>
          <div
            className="max-w-7xl max-h-[90vh] flex flex-col items-center"
            onClick={(e) => e.stopPropagation()}
          >
            {imageBlobUrls.has(lightboxImage.id) ? (
              <img
                src={imageBlobUrls.get(lightboxImage.id)}
                alt={lightboxImage.original_filename}
                className="max-w-full max-h-[80vh] object-contain rounded shadow-2xl"
              />
            ) : (
              <div className="bg-gray-800 p-8 rounded text-white">Loading image...</div>
            )}
            <div className="mt-4 text-center">
              <p className="text-white text-sm font-medium">{lightboxImage.original_filename}</p>
              <div className="flex items-center justify-center gap-4 mt-2">
                <button
                  onClick={() => handleDownloadAttachment(lightboxImage)}
                  className="flex items-center gap-2 px-4 py-2 bg-white text-gray-700 rounded hover:bg-gray-100"
                >
                  <Download className="h-4 w-4" />
                  Download
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TicketDetail;
