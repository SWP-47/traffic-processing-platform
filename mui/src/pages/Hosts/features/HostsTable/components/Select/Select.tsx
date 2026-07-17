import { useEffect, useRef, useState } from 'react';
import styles from './Select.module.css';
import selectIcon from '@/assets/select.svg';

function Select({ elements, onSelect }: { elements: string[], onSelect: (element: string) => void }) {
  const [isOpened, setIsOpened] = useState<boolean>(false);
  const [selectedElement, setSelectedElement] = useState<string>(elements[0]!);
  const selectorRef = useRef<HTMLDivElement>(null);

  const handleHeaderClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsOpened((prev) => !prev);
  };

  const handleSelection = (element: string) => {
    setSelectedElement(element);
    setIsOpened(false);
    onSelect(element);
  }

  // ---- Close on events ----
  useEffect(() => {
    if (!isOpened) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (selectorRef.current && !selectorRef.current.contains(event.target as Node)) {
        setIsOpened(false);
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpened(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpened]);

  return (
    <div ref={selectorRef} className={`${styles.selector} ${isOpened ? styles.opened : ''}`}>
      <div className={styles.header} onClick={handleHeaderClick}>
        <img src={selectIcon} className={styles.select_icon} alt="" />
        <span className={styles.selected_item}>
          {selectedElement}
        </span>
      </div>

      <div className={styles.content}>
        {
          elements.map((el, i) => (
            <p
              key={i}
              className={styles.item}
              onClick={() => handleSelection(el)}
            >
              {el}
            </p>
          ))
        }
      </div>
    </div>
  );
}

export default Select;