import { useUnit } from '@/contexts/UnitContext/useUnit';
import styles from './UnitToggle.module.css';

function UnitToggle() {
    const { unit, toggleUnit } = useUnit();

    return (
        <div className={styles.toggle} onClick={() => toggleUnit()}>
            <p className={`${unit === 'bytes' ? styles.active : ''}`}>BIT</p>
            <p className={`${unit === 'packets' ? styles.active : ''}`}>PKT</p>
        </div>
    );
}

export default UnitToggle;