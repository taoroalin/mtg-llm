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
  margin: 0 auto;
  padding: 20px;
`;

const GamePanel = styled.div`
  min-width: 0;
`;

const GameInfo = styled.div`
  text-align: center;
  margin-bottom: 20px;
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
        <GameInfo>
          <p>Active Player: {gameMaster.game_state.active_player_index + 1}</p>
          <p>Turn Step: {gameMaster.game_state.turn_step}</p>
        </GameInfo>

        {gameMaster.game_state.player_boards.map((board, i) => (
          <PlayerBoard key={i} board={board} playerIndex={i} gameId={gameId}/>
        ))}
      </GamePanel>

      <GameHistory playerHistories={gameMaster.player_observation_histories} />
    </Container>
  );
}

export default App;