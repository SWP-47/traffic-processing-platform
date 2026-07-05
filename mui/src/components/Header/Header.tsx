import { useAuth } from '@/hooks/useAuth';
import styles from './Header.module.css';
import avatarImg from '@/assets/avatar.png';
import ChannelSelector from './components/ChannelSelector/ChannelSelector.tsx';
import { NavLink } from "react-router";

function Header() {
  const { username } = useAuth();

  return (
    <div className={styles.header}>
      <div className={styles.left}>
        <div className={styles.user}>
          <img src={avatarImg} className={styles.avatar}/>
          <h1 className={styles.name}>Hello, {username}!</h1>
        </div>
        <ChannelSelector />
      </div>
      <div className={styles.links}>
        <NavLink
          to="/"
          className={({ isActive }) => isActive ? styles.active : ''}
        >
          Dashboard
        </NavLink>
        <NavLink
          to="/hosts"
          className={({ isActive }) => isActive ? styles.active : ''}
        >
          Hosts
        </NavLink>
      </div>
    </div>
  );
}

export default Header;