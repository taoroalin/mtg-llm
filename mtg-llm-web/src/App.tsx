import styled from '@emotion/styled';
import { PlayerBoard } from './components/PlayerBoard';
import { GameMaster } from './types';
import { useState, useEffect } from 'react';
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

  useEffect(() => {
    const createGame = async () => {
      const response = await fetch('http://localhost:8000/create_game', { method: 'POST' });
      const { game_id } = await response.json();
      setGameId(game_id);
      const ws = new WebSocket(`ws://localhost:8000/ws/${game_id}`);
      
      ws.onmessage = (event) => {
        const newGameMaster = JSON.parse(event.data);
        setGameMaster(newGameMaster);
      };

      return () => ws.close();
    };

    createGame();
  }, []);

  if (!gameMaster || gameId===null) return <div>Loading...</div>;

  return (
    <Container>
      <CodeHistory codeHistory={gameMaster.used_python_code} errorHistory={gameMaster.error_messages} />

      <GamePanel>
        <GameInfo>
          <h1>MTG Game Master</h1>
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