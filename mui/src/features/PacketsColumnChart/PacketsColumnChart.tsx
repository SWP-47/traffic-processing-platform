import ColumnChart from "./components/ColumnChart/ColumnChart";
import styles from './PacketsColumnChart.module.css';
import numerical_mode from '@/assets/numerical_mode.svg';
import bars_mode from '@/assets/bars_mode.svg';
import arrow_down from '@/assets/arrow_down.svg';
import arrow_up from '@/assets/arrow_up.svg';
import { useState } from "react";

export interface PacketsColumnChartData {
  packetsIn: number
  packetsOut: number
}

function PacketsColumnChart({
  packetsIn,
  packetsOut
}: PacketsColumnChartData) {
  const [mode, setMode] = useState<'numerical' | 'bars'>('numerical');

  return (
    <div className={`card ${styles.chart}`}>
      <div className={styles.header}>
        <h1 className={styles.title}>RX/TX Rate</h1>
        <button
          className={styles.mode_selector}
          onClick={() => {
            if (mode == 'bars') setMode('numerical');
            else setMode('bars');
          }}
        >
          {
            mode === 'bars' ?
            <img src={numerical_mode} /> : 
            <img src={bars_mode} />
          }
        </button>
      </div>
      <div className={styles.content_wrapper}>
        <div className={`${styles.view} ${mode === 'bars' ? styles.view_active : ''}`}>
          <ColumnChart
            data={[
              {
                value: packetsIn ?? 0,
                formatter: (value) => value.toFixed(0) + ' pkt/s',
                label: 'received'
              },
              {
                value: packetsOut ?? 0,
                formatter: (value) => value.toFixed(0) + ' pkt/s',
                label: 'sent'
              }
            ]}
          />
        </div>
        <div className={`${styles.view} ${mode === 'numerical' ? styles.view_active : ''}`}>
          <div className={styles.numerical}>
            <div className={styles.data}>
              <p className={styles.value}>{(packetsIn ?? 0).toFixed(0)}</p>
              <div className={styles.label}>
                <img src={arrow_down} className={styles.arrow} />
                <div className={styles.text}>
                  <p className={styles.unit}>pkt/s</p>
                  <p className={styles.name}>received</p>
                </div>
              </div>
            </div>
            <div className={styles.data}>
              <p className={styles.value}>{(packetsOut ?? 0).toFixed(0)}</p>
              <div className={styles.label}>
                <img src={arrow_up} className={styles.arrow} />
                <div className={styles.text}>
                  <p className={styles.unit}>pkt/s</p>
                  <p className={styles.name}>sent</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default PacketsColumnChart;