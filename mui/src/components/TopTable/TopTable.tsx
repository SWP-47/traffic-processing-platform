import styles from './TopTable.module.css';
import sortIcon from '@/assets/sort_down.svg';
import expandIcon from '@/assets/expand.svg';
import loadingIcon from '@/assets/loading.svg';
import { useEffect, useState } from 'react';

export interface ColumnData {
  name: string;
  id: string;
}

export interface TableData {
  columns: ColumnData[];
  data: (React.ReactNode)[][];
  loading?: boolean;
  onSortChange?: (column: string, direction: 'asc' | 'desc') => void;
  onExpanding?: () => void;
  onRowClick?: (e: React.MouseEvent<HTMLDivElement>, rowData: React.ReactNode[]) => void; // <-- Добавили
  defaultSortColumn: string;
}

function TopTable({ 
  columns, 
  data, 
  loading, 
  onSortChange, 
  onExpanding, 
  onRowClick,
  defaultSortColumn 
}: TableData) {
  const [sortingColumn, setSortingColumn] = useState<string>(defaultSortColumn);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  const handleSortClick = (columnId: string) => {
    if (columnId === sortingColumn) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortingColumn(columnId);
      setSortDirection('desc'); 
    }
  };

  useEffect(() => {
    if (!onSortChange || !sortingColumn) return;
    onSortChange(sortingColumn, sortDirection);
  }, [onSortChange, sortingColumn, sortDirection]);

  return (
    <div className={styles.table} style={{ '--column-count': columns.length } as React.CSSProperties}>
      <div className={styles.header}>
        {columns.map((column, i) => (
          <div 
            key={i} 
            className={`${styles.header_column} ${sortingColumn === column.id ? styles.sorting : ''}`}
            onClick={() => handleSortClick(column.id)}
          >
            <span className={styles.column_name}>{column.name}</span>
            <img 
              src={sortIcon} 
              alt="Sort" 
              className={styles.sort_icon} 
              style={{
                transform: sortingColumn === column.id && sortDirection === 'desc' ? 'rotate(180deg)' : 'rotate(0deg)',
                transition: 'transform 0.2s ease'
              }}
            />
          </div>
        ))}
      </div>
      
      <div className={styles.body}>
        {loading ? (
          <img src={loadingIcon} className={styles.loading} alt="Loading..." />
        ) : (
          data.map((row, rowIndex) => (
            <div 
              key={rowIndex} 
              className={`${styles.row} ${onRowClick ? styles.clickable_row : ''}`}
              onClick={onRowClick ? (e) => onRowClick(e, row) : undefined}
            >
              {row.map((value, cellIndex) => (
                <div key={cellIndex} className={styles.cell}>
                  {value}
                </div>
              ))}
            </div>
          ))
        )}
        
        <div className={`${styles.row} ${styles.expand_row}`} onClick={onExpanding}>
            <div className={styles.cell}>
              <span>View all entries</span>
              <img src={expandIcon} alt="Expand" />
            </div>
        </div>
      </div>
    </div>
  );
}

export default TopTable;