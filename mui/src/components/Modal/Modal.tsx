import { useEffect, useRef } from 'react';
import styles from './Modal.module.css';

interface ModalProps {
  children: React.ReactNode;
  opened: boolean;
  onClose: () => void;
}

function Modal({ children, opened, onClose }: ModalProps) {
  const contentRef = useRef<HTMLDivElement>(null);


  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    if (opened) {
      document.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [opened, onClose]);

  const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (contentRef.current && !contentRef.current.contains(e.target as Node)) {
      onClose();
    }
  };

  return (
    <div className={`${styles.modal} ${opened ? styles.opened : ''}`} onClick={handleOverlayClick}>
      <div className={styles.content} ref={contentRef}>
        {children}
      </div>
    </div>
  );
}

export default Modal;