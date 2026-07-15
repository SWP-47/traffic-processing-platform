import styles from './Loading.module.css';
import loadingIcon from '@/assets/loading.svg';

function Loading() {
  return (
    <img src={loadingIcon} className={styles.loading} alt="Loading..." />
  );
}

export default Loading;