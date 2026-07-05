import styles from './TopTable.module.css';
import sortIcon from '@/assets/sort_down.svg';
import expandIcon from '@/assets/expand.svg';
import loadingIcon from '@/assets/loading.svg';
import { useEffect, useState } from 'react';

export interface ColumnData {
  name: string,
  id: string,
  allowSorting: boolean
}

export interface TableData {
  columns: ColumnData[],
  data: (React.ReactNode)[][],
  loading?: boolean,
  onSortChange?: (column: string) => void,
  onExpanding?: () => void,
  defaultSortColumn: string;
}

function TopTable({ columns, data, loading, onSortChange, onExpanding, defaultSortColumn }: TableData) {
  const [soringColumn, setSortingColumn] = useState<string>(defaultSortColumn);

  useEffect(() => {
    if (!onSortChange || !soringColumn) return;

    onSortChange(soringColumn);
  }, [onSortChange, soringColumn])

  return (
    <div className={styles.table} style={{ '--column-count': columns.length } as React.CSSProperties}>
      <div className={styles.header}>
        {columns.map((column, i) => (
          <div 
            key={i} 
            className={`${styles.header_column} ${soringColumn == column.id ? styles.sorting : ''}`}
            onClick={() => column.allowSorting && setSortingColumn(column.id)}
          >
            <span className={styles.column_name}>{column.name}</span>
            {column.allowSorting && (
              <img src={sortIcon} alt="Sort" className={styles.sort_icon} />
            )}
          </div>
        ))}
      </div>
      
      <div className={styles.body}>
        {loading ? (
          <img src={loadingIcon} className={styles.loading} alt="Loading..." />
        ) : (
          data.map((row, rowIndex) => (
            <div key={rowIndex} className={styles.row}>
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
              <img src={expandIcon} />
            </div>
        </div>
      </div>
    </div>
  );
}

export default TopTable;