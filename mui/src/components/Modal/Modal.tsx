import { useEffect, useRef } from 'react';
import styles from './Modal.module.css';
import closeIcon from '@/assets/close.svg';
import useDelayedVisibility from '@/hooks/useDelayedVisibility';

interface ModalProps {
  children: React.ReactNode;
  opened: boolean;
  onClose: () => void;
}

function Modal({ children, opened, onClose }: ModalProps) {
  const contentRef = useRef<HTMLDivElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);
  const delayedOpen = useDelayedVisibility(opened, 300);
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        const openModals = document.querySelectorAll('[data-modal="opened"]');
        const isTopmost = openModals[openModals.length - 1] === modalRef.current;

        if (isTopmost) {
          onCloseRef.current();
        }
      }
    };

    if (opened) {
      document.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [opened]);

  const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (contentRef.current && !contentRef.current.contains(e.target as Node)) {
      e.stopPropagation();
      onClose();
    }
  };

  return (
    <div 
      data-modal={opened ? 'opened' : 'closed'} 
      ref={modalRef}
      className={`${styles.modal} ${opened ? styles.opened : ''}`} 
      onClick={handleOverlayClick}
    >
      <div className={styles.content_wrapper}>
        <div className={styles.close_button} onClick={() => onClose()}>
          <img src={closeIcon} alt="Close" />
        </div>
        <div className={styles.content} ref={contentRef}>
          {/* Hide content with delay to play close animation */}
          {(opened || delayedOpen) && children}
        </div>
      </div>
    </div>
  );
}

export default Modal;