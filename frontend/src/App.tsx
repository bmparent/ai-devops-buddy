import { useEffect, useState } from 'react';
import { getMessage } from './api';

export default function App() {
  const [message, setMessage] = useState('');
  useEffect(() => {
    getMessage().then(setMessage);
  }, []);
  return <h1>{message}</h1>;
}
