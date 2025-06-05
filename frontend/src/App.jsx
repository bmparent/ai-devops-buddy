import { useEffect, useState } from 'react';

function App() {
  const [ping, setPing] = useState('');
  useEffect(() => {
    fetch('http://localhost:8000/ping')
      .then(res => res.json())
      .then(data => setPing(data.ping))
      .catch(() => setPing('error'));
  }, []);
  return <div>{ping}</div>;
}

export default App;
