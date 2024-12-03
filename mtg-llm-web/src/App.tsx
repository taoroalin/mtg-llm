import styled from '@emotion/styled';
import { PlayerBoard } from './components/PlayerBoard';
import { GameMaster } from './types';
import { useState, useEffect, useRef } from 'react';
import { GameHistory } from './components/GameHistory';
import { CodeHistory } from './components/CodeHistory';
import { useParams, useNavigate, BrowserRouter, Routes, Route } from 'react-router-dom';

const Container = styled.div`
  display: grid;
  grid-template-columns: 300px 1fr 300px;
  gap: 20px;
  margin: 0;
  padding: 0;
  height: 100vh;
  overflow: hidden;
`;

const GamePanel = styled.div`
  min-width: 0;
  overflow-y: auto;
`;


const HomePage = () => {
  const navigate = useNavigate();
  const [games, setGames] = useState<{ongoing_games: string[], finished_games: string[]}>({ ongoing_games: [], finished_games: [] });

  useEffect(() => {
    fetch('http://localhost:8000/games')
      .then(res => res.json())
      .then(setGames);
  }, []);

  const createNewGame = async () => {
    const response = await fetch('http://localhost:8000/create_game', { method: 'POST' });
    const { game_id } = await response.json();
    navigate(`/game/${game_id}`);
  };

  return (
    <div style={{ padding: '20px' }}>
      <h1>Magic Game Browser</h1>
      <button onClick={createNewGame}>Create New Game</button>
      
      <h2>Ongoing Games</h2>
      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
        {games.ongoing_games.map(id => (
          <button key={id} onClick={() => navigate(`/gameview/${id}`)}>
            Game {id.slice(0, 8)}
          </button>
        ))}
      </div>

      <h2>Finished Games</h2>
      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
        {games.finished_games.map(id => (
          <button key={id} onClick={() => navigate(`/gameview/${id}`)}>
            Game {id.slice(0, 8)}
          </button>
        ))}
      </div>
    </div>
  );
};

const GameView = ({ viewOnly }: { viewOnly: boolean }) => {
  const { gameId } = useParams();
  // ... existing game state logic ...
  const [gameMaster, setGameMaster] = useState<GameMaster | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!gameId) return;
    if (viewOnly) {
      fetch(`http://localhost:8000/get_game/${gameId}`)
        .then(res => res.json())
        .then(setGameMaster);
    } else {
      const ws = new WebSocket(`ws://localhost:8000/ws/${gameId}`);
      wsRef.current = ws;

    ws.onmessage = (event) => {
      if (wsRef.current === ws) {
        const newGameMaster = JSON.parse(event.data);
        setGameMaster(newGameMaster);
      } else {
        ws.close();
        }
      };
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [gameId, viewOnly]);

  if (!gameMaster || !gameId) return <div>Loading...</div>;

  return (
    <Container>
      <CodeHistory codeHistory={gameMaster.used_python_code} errorHistory={gameMaster.error_messages} />

      <GamePanel>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '20px', marginBottom: '10px', marginLeft: '10px', marginRight: '10px' }}>
            <div>
              <p>Library: {gameMaster.game_state.player_boards[0].library.length}</p>
              <p>Graveyard: {gameMaster.game_state.player_boards[0].graveyard.length}</p>
              <p>Exile: {gameMaster.game_state.player_boards[0].exile.length}</p>
            </div>
            <div style={{ textAlign: 'center' }}>
              <h2>Game State</h2>
              <p>Turn Step: {gameMaster.game_state.turn_step}</p>
              <p>Turn: {gameMaster.game_state.turn_number}</p>
            </div>
            <div style={{ textAlign: 'right' }}>
              <p>Library: {gameMaster.game_state.player_boards[1].library.length}</p>
              <p>Graveyard: {gameMaster.game_state.player_boards[1].graveyard.length}</p>
              <p>Exile: {gameMaster.game_state.player_boards[1].exile.length}</p>
            </div>
          </div>

        {gameMaster.game_state.player_boards.map((board, i) => (
          <PlayerBoard key={i} board={board} playerIndex={i} gameId={gameId}/>
        ))}
      </GamePanel>

      <GameHistory playerHistories={gameMaster.player_observation_histories} />
    </Container>
  );
};

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/game/:gameId" element={<GameView viewOnly={false}/>} />
        <Route path="/gameview/:gameId" element={<GameView viewOnly={true}/>} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;