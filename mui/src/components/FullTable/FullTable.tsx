import React from 'react';
import styles from './FullTable.module.css';
import sortIcon from '@/assets/sort.svg';
import sortDownIcon from '@/assets/sort_down.svg';
import sortUpIcon from '@/assets/sort_up.svg';
import backIcon from '@/assets/back.svg';
import nextIcon from '@/assets/next.svg';

export interface ColumnData {
  name: string;
  id: string;
  allowSorting: boolean;
}

export interface FullTableProps {
  columns: ColumnData[];
  data: React.ReactNode[][];
  loading?: boolean;

  // Sorting State & Callbacks
  sortColumnId?: string;
  sortDirection?: 'asc' | 'desc';
  onSortChange?: (columnId: string, direction: 'asc' | 'desc') => void;

  // Pagination State & Callbacks
  currentPage: number;
  amountOfPages: number;
  limit: number;
  onPageChange?: (page: number) => void;
  onLimitChange?: (limit: number) => void;

  // Row Interactions
  onRowClick?: (rowIndex: number, rowData: React.ReactNode[]) => void;
}

// Helper to generate a smart pagination range (e.g., 1 ... 4 5 6 ... 10)
const getPaginationRange = (current: number, total: number) => {
  if (total <= 8) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }

  const result: (number | string)[] = [];

  if (current <= 4) {
    result.push(1, 2, 3, 4, 5, 6, '...', total);
  } else if (current >= total - 3) {
    result.push(1, '...', total - 5, total - 4, total - 3, total - 2, total - 1, total);
  } else {
    result.push(1, '...', current - 1, current, current + 1, '...', total - 1, total);
  }

  return result;
};

function FullTable({
  columns,
  data,
  sortColumnId,
  sortDirection = 'desc',
  onSortChange,
  currentPage,
  amountOfPages,
  limit,
  onPageChange,
  onLimitChange,
  onRowClick,
}: FullTableProps) {

  const handleSortClick = (columnId: string) => {
    if (!onSortChange) return;
    let newDirection: 'asc' | 'desc' = 'desc';
    if (sortColumnId === columnId) {
      newDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    }
    onSortChange(columnId, newDirection);
  };

  const handlePageClick = (page: number | string) => {
    if (typeof page === 'number' && onPageChange && page !== currentPage) {
      onPageChange(page);
    }
  };

  const paginationRange = getPaginationRange(currentPage, amountOfPages);

  return (
    <div className={styles.table} style={{ '--column-count': columns.length } as React.CSSProperties}>

      {/* Headers */}
      {columns.map(column => (
        <div
          key={column.id}
          className={[
            styles.cell,
            styles.header,
            column.id === sortColumnId ? styles.sorting : '',
          ].join(' ')}
          onClick={() => column.allowSorting && handleSortClick(column.id)}
        >
          <p>{column.name}</p>
          {column.allowSorting && (
            <div className={`${styles.sort_wrapper} ${sortDirection === 'asc' ? styles.sort_asc : styles.sort_desc}`}>
              <img src={sortIcon} alt="Sort" className={`${styles.sort_icon} ${styles.sort_select_icon}`} />
              <img src={sortDownIcon} alt="Sort Down" className={`${styles.sort_icon} ${styles.sort_desc_icon}`} />
              <img src={sortUpIcon} alt="Sort Up" className={`${styles.sort_icon} ${styles.sort_asc_icon}`} />
            </div>
          )}
        </div>
      ))}

      {/* Data Rows */}
      {data.map((row, rowIndex) => (
        <div
          key={rowIndex}
          className={styles.row}
          onClick={() => onRowClick?.(rowIndex, row)}
        >
          {row.map((cell, cellIndex) => (
            <div key={cellIndex} className={styles.cell}>
              {cell}
            </div>
          ))}
        </div>
      ))}

      {/* Pagination Controls */}
      <div className={styles.pagination_controls}>
        <div className={styles.select_limit}>
          <p className={styles.label}>Results per page:</p>
          <select value={limit} onChange={(e) => onLimitChange?.(Number(e.target.value))}>
            <option value="10">10</option>
            <option value="20">20</option>
            <option value="50">50</option>
            <option value="100">100</option>
          </select>
        </div>

        <div className={styles.select_page}>
          <div
            className={`${styles.back_button} ${currentPage === 1 ? styles.disabled : ''}`}
            onClick={() => currentPage > 1 && onPageChange?.(currentPage - 1)}
          >
            <img src={backIcon} alt="Previous" />
            <p>Previous</p>
          </div>

          <div className={styles.pages}>
            {paginationRange.map((page, idx) => (
              <p
                key={idx}
                className={`${styles.page} ${page === currentPage ? styles.selected : ''} ${page === '...' ? styles.ellipses : ''}`}
                onClick={() => handlePageClick(page)}
              >
                {page}
              </p>
            ))}
          </div>

          <div
            className={`${styles.next_button} ${currentPage === amountOfPages ? styles.disabled : ''}`}
            onClick={() => currentPage < amountOfPages && onPageChange?.(currentPage + 1)}
          >
            <p>Next</p>
            <img src={nextIcon} alt="Next" />
          </div>
        </div>
      </div>
    </div>
  );
}

export default FullTable;