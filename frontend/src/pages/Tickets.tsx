import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { ticketsApi, Ticket } from '../api/tickets';
import { AlertTriangle } from 'lucide-react';
import { formatInCET } from '../utils/dateFormat';
import Pagination from '../components/Pagination';

const ITEMS_PER_PAGE = 50;

interface ColumnWidths {
  ticketNumber: number;
  status: number;
  amazonOrder: number;
  transaction: number;
  poNumber: number;
  aiDecisions: number;
  lastUpdated: number;
}

const DEFAULT_WIDTHS: ColumnWidths = {
  ticketNumber: 150,
  status: 120,
  amazonOrder: 180,
  transaction: 150,
  poNumber: 150,
  aiDecisions: 120,
  lastUpdated: 180,
};

const Tickets: React.FC = () => {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [filteredTickets, setFilteredTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [showEscalated, setShowEscalated] = useState(false);
  const [hideClosedTickets, setHideClosedTickets] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [columnWidths, setColumnWidths] = useState<ColumnWidths>(DEFAULT_WIDTHS);
  const [resizing, setResizing] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    ticketNumber: '',
    status: '',
    amazonOrder: '',
    transaction: '',
    poNumber: '',
  });
  const startXRef = useRef<number>(0);
  const startWidthRef = useRef<number>(0);
  const navigate = useNavigate();

  // Load column widths from localStorage
  useEffect(() => {
    const savedWidths = localStorage.getItem('ticketColumnWidths');
    if (savedWidths) {
      try {
        setColumnWidths(JSON.parse(savedWidths));
      } catch (e) {
        console.error('Failed to parse saved column widths:', e);
      }
    }
  }, []);

  useEffect(() => {
    loadTickets();
  }, [showEscalated, currentPage]);

  const loadTickets = async () => {
    try {
      const data = await ticketsApi.getTickets({
        limit: ITEMS_PER_PAGE,
        offset: (currentPage - 1) * ITEMS_PER_PAGE,
        escalated_only: showEscalated,
      });
      setTickets(data);
      setFilteredTickets(data);
      // Estimate total based on whether we got a full page
      setTotalItems(data.length === ITEMS_PER_PAGE ? currentPage * ITEMS_PER_PAGE + 1 : (currentPage - 1) * ITEMS_PER_PAGE + data.length);
    } catch (error) {
      console.error('Failed to load tickets:', error);
    } finally {
      setLoading(false);
    }
  };

  // Apply filters
  useEffect(() => {
    let filtered = tickets;

    // Filter out closed tickets if hideClosedTickets is enabled
    if (hideClosedTickets) {
      filtered = filtered.filter(ticket =>
        !ticket.custom_status || !ticket.custom_status.is_closed
      );
    }

    if (filters.ticketNumber) {
      filtered = filtered.filter(ticket =>
        ticket.ticket_number.toLowerCase().includes(filters.ticketNumber.toLowerCase())
      );
    }

    if (filters.status) {
      filtered = filtered.filter(ticket =>
        ticket.status.toLowerCase().includes(filters.status.toLowerCase())
      );
    }

    if (filters.amazonOrder) {
      filtered = filtered.filter(ticket =>
        ticket.order_number?.toLowerCase().includes(filters.amazonOrder.toLowerCase())
      );
    }

    if (filters.transaction) {
      filtered = filtered.filter(ticket =>
        ticket.ticket_number.toLowerCase().includes(filters.transaction.toLowerCase())
      );
    }

    if (filters.poNumber) {
      filtered = filtered.filter(ticket =>
        ticket.purchase_order_number?.toLowerCase().includes(filters.poNumber.toLowerCase())
      );
    }

    setFilteredTickets(filtered);
  }, [tickets, filters, hideClosedTickets]);

  const handleFilterChange = (column: string, value: string) => {
    setFilters(prev => ({
      ...prev,
      [column]: value,
    }));
  };

  const handleMouseDown = (e: React.MouseEvent, column: keyof ColumnWidths) => {
    e.preventDefault();
    setResizing(column);
    startXRef.current = e.clientX;
    startWidthRef.current = columnWidths[column];
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!resizing) return;
    const diff = e.clientX - startXRef.current;
    const newWidth = Math.max(80, startWidthRef.current + diff);
    setColumnWidths((prev) => ({
      ...prev,
      [resizing]: newWidth,
    }));
  };

  const handleMouseUp = () => {
    if (resizing) {
      localStorage.setItem('ticketColumnWidths', JSON.stringify(columnWidths));
      setResizing(null);
    }
  };

  useEffect(() => {
    if (resizing) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      return () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [resizing, columnWidths]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Tickets</h1>
          <p className="text-gray-600 mt-1">View and manage support tickets</p>
        </div>
        <div className="flex items-center gap-6">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showEscalated}
              onChange={(e) => setShowEscalated(e.target.checked)}
              className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            <span className="text-sm font-medium text-gray-700">Show escalated only</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={hideClosedTickets}
              onChange={(e) => setHideClosedTickets(e.target.checked)}
              className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            <span className="text-sm font-medium text-gray-700">Hide closed tickets</span>
          </label>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-x-auto">
        <table className="divide-y divide-gray-200" style={{ tableLayout: 'fixed' }}>
          <thead className="bg-gray-50">
            <tr>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider relative"
                style={{ width: `${columnWidths.ticketNumber}px` }}
              >
                <div className="mb-1">Ticket #</div>
                <input
                  type="text"
                  value={filters.ticketNumber}
                  onChange={(e) => handleFilterChange('ticketNumber', e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  placeholder="Filter..."
                  className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
                <div
                  className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-indigo-500"
                  onMouseDown={(e) => handleMouseDown(e, 'ticketNumber')}
                />
              </th>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider relative"
                style={{ width: `${columnWidths.status}px` }}
              >
                <div className="mb-1">Status</div>
                <input
                  type="text"
                  value={filters.status}
                  onChange={(e) => handleFilterChange('status', e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  placeholder="Filter..."
                  className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
                <div
                  className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-indigo-500"
                  onMouseDown={(e) => handleMouseDown(e, 'status')}
                />
              </th>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider relative"
                style={{ width: `${columnWidths.amazonOrder}px` }}
              >
                <div className="mb-1">Amazon Order Nr</div>
                <input
                  type="text"
                  value={filters.amazonOrder}
                  onChange={(e) => handleFilterChange('amazonOrder', e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  placeholder="Filter..."
                  className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
                <div
                  className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-indigo-500"
                  onMouseDown={(e) => handleMouseDown(e, 'amazonOrder')}
                />
              </th>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider relative"
                style={{ width: `${columnWidths.transaction}px` }}
              >
                <div className="mb-1">Transaction Nr</div>
                <input
                  type="text"
                  value={filters.transaction}
                  onChange={(e) => handleFilterChange('transaction', e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  placeholder="Filter..."
                  className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
                <div
                  className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-indigo-500"
                  onMouseDown={(e) => handleMouseDown(e, 'transaction')}
                />
              </th>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider relative"
                style={{ width: `${columnWidths.poNumber}px` }}
              >
                <div className="mb-1">PO Number</div>
                <input
                  type="text"
                  value={filters.poNumber}
                  onChange={(e) => handleFilterChange('poNumber', e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  placeholder="Filter..."
                  className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
                <div
                  className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-indigo-500"
                  onMouseDown={(e) => handleMouseDown(e, 'poNumber')}
                />
              </th>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider relative"
                style={{ width: `${columnWidths.aiDecisions}px` }}
              >
                <div className="mb-1">AI Decisions</div>
                <div
                  className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-indigo-500"
                  onMouseDown={(e) => handleMouseDown(e, 'aiDecisions')}
                />
              </th>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider relative"
                style={{ width: `${columnWidths.lastUpdated}px` }}
              >
                <div className="mb-1">Last Updated</div>
                <div
                  className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-indigo-500"
                  onMouseDown={(e) => handleMouseDown(e, 'lastUpdated')}
                />
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredTickets.map((ticket) => (
              <tr
                key={ticket.ticket_number}
                onClick={() => navigate(`/tickets/${ticket.ticket_number}`)}
                className="hover:bg-gray-50 cursor-pointer"
              >
                <td className="px-6 py-4 whitespace-nowrap overflow-hidden text-ellipsis" style={{ width: `${columnWidths.ticketNumber}px` }}>
                  <div className="flex items-center gap-2">
                    {ticket.escalated && (
                      <AlertTriangle className="h-4 w-4 text-red-500" />
                    )}
                    <span className="text-sm font-medium text-gray-900">
                      {ticket.ticket_number}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap overflow-hidden text-ellipsis" style={{ width: `${columnWidths.status}px` }}>
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      ticket.escalated
                        ? 'bg-red-100 text-red-800'
                        : 'bg-green-100 text-green-800'
                    }`}
                  >
                    {ticket.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 overflow-hidden text-ellipsis" style={{ width: `${columnWidths.amazonOrder}px` }}>
                  {ticket.order_number || '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 overflow-hidden text-ellipsis" style={{ width: `${columnWidths.transaction}px` }}>
                  {ticket.ticket_number}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 overflow-hidden text-ellipsis" style={{ width: `${columnWidths.poNumber}px` }}>
                  {ticket.purchase_order_number || '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap overflow-hidden text-ellipsis" style={{ width: `${columnWidths.aiDecisions}px` }}>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                    {ticket.ai_decision_count}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 overflow-hidden text-ellipsis" style={{ width: `${columnWidths.lastUpdated}px` }}>
                  {formatInCET(ticket.last_updated)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <Pagination
          currentPage={currentPage}
          totalItems={totalItems}
          itemsPerPage={ITEMS_PER_PAGE}
          onPageChange={setCurrentPage}
        />
      </div>
    </div>
  );
};

export default Tickets;
