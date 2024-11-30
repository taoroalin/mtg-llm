import styled from '@emotion/styled';
import { PlayerBoard } from './components/PlayerBoard';
import { GameMaster } from './types';
import { useState, useEffect } from 'react';

const Container = styled.div`
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
`;

const GameInfo = styled.div`
  text-align: center;
  margin-bottom: 20px;
`;

function App() {
  const [gameMaster, setGameMaster] = useState<GameMaster | null>(null); // Changed from GameState to any

  useEffect(() => {
    const createGame = async () => {
      const response = await fetch('http://localhost:8000/create_game', { method: 'POST' });
      const { game_id } = await response.json();
      const ws = new WebSocket(`ws://localhost:8000/ws/${game_id}`);
      
      ws.onmessage = (event) => {
        const newGameMaster = JSON.parse(event.data); // Changed to accept gamemaster
        setGameMaster(newGameMaster);
      };

      return () => ws.close();
    };

    createGame();
  }, []);

  if (!gameMaster) return <div>Loading...</div>;

  return (
    <Container>
      <GameInfo>
        <h1>MTG Game Master</h1>
        <p>Active Player: {gameMaster.game_state.active_player_index + 1}</p>
        <p>Turn Step: {gameMaster.game_state.turn_step}</p>
      </GameInfo>

      {gameMaster.game_state.player_boards.map((board, i) => (
        <PlayerBoard key={i} board={board} playerIndex={i} />
      ))}
    </Container>
  );
}

export default App;