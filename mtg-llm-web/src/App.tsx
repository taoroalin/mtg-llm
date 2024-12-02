import styled from '@emotion/styled';
import { PlayerBoard } from './components/PlayerBoard';
import { GameMaster } from './types';
import { useState, useEffect, useRef } from 'react';
import { GameHistory } from './components/GameHistory';
import { CodeHistory } from './components/CodeHistory';

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


function App() {
  const [gameMaster, setGameMaster] = useState<GameMaster | null>(null);
  const [gameId, setGameId] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const createGame = async () => {
      const response = await fetch('http://localhost:8000/create_game', { method: 'POST' });
      const { game_id } = await response.json();
      console.log("Creating game", game_id);
      setGameId(game_id);

      if (wsRef.current) {
        wsRef.current.close();
      }

      const ws = new WebSocket(`ws://localhost:8000/ws/${game_id}`);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        if (wsRef.current === ws) {
          const newGameMaster = JSON.parse(event.data);
          setGameMaster(newGameMaster);
        }else{
          ws.close();
        }
      };
    }
    createGame();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  if (!gameMaster || gameId===null) return <div>Loading...</div>;

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
}

export default App;