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
  customerName: number;
  poNumber: number;
  lastUpdated: number;
}

const WIDTHS_VERSION = 2; // Increment this when changing DEFAULT_WIDTHS

const DEFAULT_WIDTHS: ColumnWidths = {
  ticketNumber: 150,
  status: 120,
  amazonOrder: 180,
  customerName: 130,
  poNumber: 150,
  lastUpdated: 180,
};

const Tickets: React.FC = () => {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [filteredTickets, setFilteredTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [showEscalated, setShowEscalated] = useState(false);
  const [showClosed, setShowClosed] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [columnWidths, setColumnWidths] = useState<ColumnWidths>(DEFAULT_WIDTHS);
  const [resizing, setResizing] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    ticketNumber: { value: '', operator: 'contains' },
    status: { value: '', operator: 'contains' },
    amazonOrder: { value: '', operator: 'contains' },
    customerName: { value: '', operator: 'contains' },
    poNumber: { value: '', operator: 'contains' },
  });
  const startXRef = useRef<number>(0);
  const startWidthRef = useRef<number>(0);
  const navigate = useNavigate();

  // Load column widths from localStorage with version check
  useEffect(() => {
    const savedVersion = localStorage.getItem('ticketColumnWidthsVersion');
    const savedWidths = localStorage.getItem('ticketColumnWidths');

    // If version doesn't match or doesn't exist, use new defaults
    if (savedVersion !== String(WIDTHS_VERSION) || !savedWidths) {
      setColumnWidths(DEFAULT_WIDTHS);
      localStorage.setItem('ticketColumnWidths', JSON.stringify(DEFAULT_WIDTHS));
      localStorage.setItem('ticketColumnWidthsVersion', String(WIDTHS_VERSION));
    } else {
      try {
        setColumnWidths(JSON.parse(savedWidths));
      } catch (e) {
        console.error('Failed to parse saved column widths:', e);
        setColumnWidths(DEFAULT_WIDTHS);
      }
    }
  }, []);

  useEffect(() => {
    loadTickets();
  }, [showEscalated, currentPage]);

  // Auto-refresh tickets every 30 seconds to pick up updates like PO numbers
  useEffect(() => {
    const intervalId = setInterval(() => {
      loadTickets();
    }, 30000); // 30 seconds

    return () => clearInterval(intervalId);
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

  // Helper function to apply filter operator
  const applyFilter = (value: string | null | undefined, filterValue: string, operator: string): boolean => {
    if (!filterValue) return true;
    if (!value) return false;

    const lowerValue = value.toLowerCase();
    const lowerFilter = filterValue.toLowerCase();

    switch (operator) {
      case 'contains':
        return lowerValue.includes(lowerFilter);
      case 'not_contains':
        return !lowerValue.includes(lowerFilter);
      case 'begins_with':
        return lowerValue.startsWith(lowerFilter);
      case 'ends_with':
        return lowerValue.endsWith(lowerFilter);
      case 'equals':
        return lowerValue === lowerFilter;
      case 'not_equals':
        return lowerValue !== lowerFilter;
      default:
        return lowerValue.includes(lowerFilter);
    }
  };

  // Apply filters
  useEffect(() => {
    let filtered = tickets;

    // Filter out closed tickets by default
    if (!showClosed) {
      filtered = filtered.filter(ticket =>
        !ticket.custom_status?.is_closed
      );
    }

    if (filters.ticketNumber.value) {
      filtered = filtered.filter(ticket =>
        applyFilter(ticket.ticket_number, filters.ticketNumber.value, filters.ticketNumber.operator)
      );
    }

    if (filters.status.value) {
      filtered = filtered.filter(ticket =>
        applyFilter(ticket.custom_status?.name, filters.status.value, filters.status.operator)
      );
    }

    if (filters.amazonOrder.value) {
      filtered = filtered.filter(ticket =>
        applyFilter(ticket.order_number, filters.amazonOrder.value, filters.amazonOrder.operator)
      );
    }

    if (filters.customerName.value) {
      filtered = filtered.filter(ticket =>
        applyFilter(ticket.customer_name, filters.customerName.value, filters.customerName.operator)
      );
    }

    if (filters.poNumber.value) {
      filtered = filtered.filter(ticket =>
        applyFilter(ticket.purchase_order_number, filters.poNumber.value, filters.poNumber.operator)
      );
    }

    setFilteredTickets(filtered);
  }, [tickets, filters, showClosed]);

  const handleFilterChange = (column: string, value: string) => {
    setFilters(prev => ({
      ...prev,
      [column]: { ...prev[column as keyof typeof prev], value },
    }));
  };

  const handleOperatorChange = (column: string, operator: string) => {
    setFilters(prev => ({
      ...prev,
      [column]: { ...prev[column as keyof typeof prev], operator },
    }));
  };

  const handleMouseDown = (e: React.MouseEvent, column: keyof ColumnWidths) => {
    e.preventDefault();
    e.stopPropagation();
    setResizing(column);
    startXRef.current = e.clientX;
    startWidthRef.current = columnWidths[column];
  };

  useEffect(() => {
    if (!resizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      const diff = e.clientX - startXRef.current;
      const newWidth = Math.max(80, startWidthRef.current + diff);
      setColumnWidths((prev) => ({
        ...prev,
        [resizing]: newWidth,
      }));
    };

    const handleMouseUp = () => {
      setColumnWidths((prev) => {
        localStorage.setItem('ticketColumnWidths', JSON.stringify(prev));
        localStorage.setItem('ticketColumnWidthsVersion', String(WIDTHS_VERSION));
        return prev;
      });
      setResizing(null);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [resizing]);

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
              checked={showClosed}
              onChange={(e) => setShowClosed(e.target.checked)}
              className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            <span className="text-sm font-medium text-gray-700">Show closed tickets</span>
          </label>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-x-auto">
        <table
          className="divide-y divide-gray-200"
          style={{
            tableLayout: 'fixed',
            width: `${Object.values(columnWidths).reduce((sum, width) => sum + width, 0)}px`
          }}
        >
          <thead className="bg-gray-50">
            <tr>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider relative"
                style={{ width: `${columnWidths.ticketNumber}px` }}
              >
                <div className="mb-1">Ticket #</div>
                <select
                  value={filters.ticketNumber.operator}
                  onChange={(e) => handleOperatorChange('ticketNumber', e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  className="w-full mb-1 px-1 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-indigo-500 bg-white"
                  title="Filter operator"
                >
                  <option value="contains">Contains</option>
                  <option value="not_contains">Not contains</option>
                  <option value="begins_with">Begins with</option>
                  <option value="ends_with">Ends with</option>
                  <option value="equals">Equals</option>
                  <option value="not_equals">Not equals</option>
                </select>
                <input
                  type="text"
                  value={filters.ticketNumber.value}
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
                <select
                  value={filters.status.operator}
                  onChange={(e) => handleOperatorChange('status', e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  className="w-full mb-1 px-1 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-indigo-500 bg-white"
                  title="Filter operator"
                >
                  <option value="contains">Contains</option>
                  <option value="not_contains">Not contains</option>
                  <option value="begins_with">Begins with</option>
                  <option value="ends_with">Ends with</option>
                  <option value="equals">Equals</option>
                  <option value="not_equals">Not equals</option>
                </select>
                <input
                  type="text"
                  value={filters.status.value}
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
                <select
                  value={filters.amazonOrder.operator}
                  onChange={(e) => handleOperatorChange('amazonOrder', e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  className="w-full mb-1 px-1 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-indigo-500 bg-white"
                  title="Filter operator"
                >
                  <option value="contains">Contains</option>
                  <option value="not_contains">Not contains</option>
                  <option value="begins_with">Begins with</option>
                  <option value="ends_with">Ends with</option>
                  <option value="equals">Equals</option>
                  <option value="not_equals">Not equals</option>
                </select>
                <input
                  type="text"
                  value={filters.amazonOrder.value}
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
                style={{ width: `${columnWidths.poNumber}px` }}
              >
                <div className="mb-1">PO #</div>
                <select
                  value={filters.poNumber.operator}
                  onChange={(e) => handleOperatorChange('poNumber', e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  className="w-full mb-1 px-1 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-indigo-500 bg-white"
                  title="Filter operator"
                >
                  <option value="contains">Contains</option>
                  <option value="not_contains">Not contains</option>
                  <option value="begins_with">Begins with</option>
                  <option value="ends_with">Ends with</option>
                  <option value="equals">Equals</option>
                  <option value="not_equals">Not equals</option>
                </select>
                <input
                  type="text"
                  value={filters.poNumber.value}
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
                style={{ width: `${columnWidths.customerName}px` }}
              >
                <div className="mb-1">Customer Name</div>
                <select
                  value={filters.customerName.operator}
                  onChange={(e) => handleOperatorChange('customerName', e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  className="w-full mb-1 px-1 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-indigo-500 bg-white"
                  title="Filter operator"
                >
                  <option value="contains">Contains</option>
                  <option value="not_contains">Not contains</option>
                  <option value="begins_with">Begins with</option>
                  <option value="ends_with">Ends with</option>
                  <option value="equals">Equals</option>
                  <option value="not_equals">Not equals</option>
                </select>
                <input
                  type="text"
                  value={filters.customerName.value}
                  onChange={(e) => handleFilterChange('customerName', e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  placeholder="Filter..."
                  className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
                <div
                  className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-indigo-500"
                  onMouseDown={(e) => handleMouseDown(e, 'customerName')}
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
                  {ticket.custom_status ? (
                    <span
                      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                      style={{
                        backgroundColor: ticket.custom_status.color + '20',
                        color: ticket.custom_status.color
                      }}
                    >
                      {ticket.custom_status.name}
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                      No status
                    </span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 overflow-hidden text-ellipsis" style={{ width: `${columnWidths.amazonOrder}px` }}>
                  {ticket.order_number || '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 overflow-hidden text-ellipsis" style={{ width: `${columnWidths.poNumber}px` }}>
                  {ticket.purchase_order_number || '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 overflow-hidden text-ellipsis" style={{ width: `${columnWidths.customerName}px` }}>
                  {ticket.customer_name || '-'}
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
