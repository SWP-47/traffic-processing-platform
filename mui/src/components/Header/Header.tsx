import { useAuth } from '@/hooks/useAuth';
import style from './Header.module.css';
import avatarImg from '@/assets/avatar.png';
import ChannelSelector from './components/ChannelSelector/ChannelSelector';

function Header() {
  const { username } = useAuth();

  return (
    <div className={style.header}>
      <div className={style.left}>
        <div className={style.user}>
          <img src={avatarImg} className={style.avatar}/>
          <h1 className={style.name}>Hello, {username}!</h1>
        </div>
        <ChannelSelector />
      </div>
    </div>
  );
}

export default Header;