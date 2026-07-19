import ColumnChart from "./components/ColumnChart/ColumnChart";
import styles from './PacketsColumnChart.module.css';
import numerical_mode from '@/assets/numerical_mode.svg';
import bars_mode from '@/assets/bars_mode.svg';
import arrow_down from '@/assets/arrow_down.svg';
import arrow_up from '@/assets/arrow_up.svg';
import { useMemo, useState } from "react";
import { useUnit } from "@/contexts/UnitContext/useUnit";
import { formatSplit } from "@/utils/information";
import type { FormattedValue } from "@/utils/information";

export interface PacketsColumnChartData {
  packetsIn: number;
  packetsOut: number;
  bytesIn: number;
  bytesOut: number;
}

function PacketsColumnChart({
  packetsIn,
  packetsOut,
  bytesIn,
  bytesOut,
}: PacketsColumnChartData) {
  const [mode, setMode] = useState<'numerical' | 'bars'>('numerical');
  const { unit } = useUnit();

  const valueIn = unit === 'bytes' ? bytesIn : packetsIn;
  const valueOut = unit === 'bytes' ? bytesOut : packetsOut;

  const formattedIn: FormattedValue = useMemo(
    () => formatSplit(unit, valueIn),
    [unit, valueIn],
  );
  const formattedOut: FormattedValue = useMemo(
    () => formatSplit(unit, valueOut),
    [unit, valueOut],
  );

  return (
    <div className={`card ${styles.chart}`}>
      <div className={styles.header}>
        <h1 className={styles.title}>RX/TX Rate</h1>
        <button
          className={styles.mode_selector}
          onClick={() => setMode((m) => (m === 'bars' ? 'numerical' : 'bars'))}
        >
          {mode === 'bars' ? (
            <img src={numerical_mode} alt="Switch to numerical mode" />
          ) : (
            <img src={bars_mode} alt="Switch to bars mode" />
          )}
        </button>
      </div>

      <div className={styles.content_wrapper}>
        {/* Bars mode */}
        <div className={`${styles.view} ${mode === 'bars' ? styles.view_active : ''}`}>
          <ColumnChart
            data={[
              {
                value: valueIn,
                formatter: () => `${formattedIn.value} ${formattedIn.unit}`,
                label: 'received',
              },
              {
                value: valueOut,
                formatter: () => `${formattedOut.value} ${formattedOut.unit}`,
                label: 'sent',
              },
            ]}
          />
        </div>

        {/* Numerical mode */}
        <div className={`${styles.view} ${mode === 'numerical' ? styles.view_active : ''}`}>
          <div className={styles.numerical}>
            <div className={styles.data}>
              <p className={styles.value}>{formattedIn.value}</p>
              <div className={styles.label}>
                <img src={arrow_down} className={styles.arrow} alt="" />
                <div className={styles.text}>
                  <p className={styles.unit}>{formattedIn.unit}</p>
                  <p className={styles.name}>received</p>
                </div>
              </div>
            </div>

            <div className={styles.data}>
              <p className={styles.value}>{formattedOut.value}</p>
              <div className={styles.label}>
                <img src={arrow_up} className={styles.arrow} alt="" />
                <div className={styles.text}>
                  <p className={styles.unit}>{formattedOut.unit}</p>
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