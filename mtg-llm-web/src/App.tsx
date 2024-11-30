import styled from '@emotion/styled';
import { PlayerBoard } from './components/PlayerBoard';
import { GameState } from './types';
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
  // This would be replaced with your actual game state
  const [gameState, setGameState] = useState<GameState | null>(null);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws');
    
    ws.onmessage = (event) => {
      const newState = JSON.parse(event.data);
      setGameState(newState);
    };

    return () => ws.close();
  }, []);

  if (!gameState) return <div>Loading...</div>;

  return (
    <Container>
      <GameInfo>
        <h1>MTG Game State</h1>
        <p>Active Player: {gameState.active_player_index + 1}</p>
        <p>Turn Step: {gameState.turn_step}</p>
      </GameInfo>

      {gameState.player_boards.map((board, i) => (
        <PlayerBoard key={i} board={board} playerIndex={i} />
      ))}
    </Container>
  );
}

export default App;