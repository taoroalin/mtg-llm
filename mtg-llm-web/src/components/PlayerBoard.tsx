import styled from '@emotion/styled';
import { Card } from './Card';
import { PlayerBoard as PlayerBoardType } from '../types';

const BoardContainer = styled.div`
  padding: 20px;
  border: 1px solid #ccc;
  margin: 10px;
`;

const Zone = styled.div`
  margin: 10px 0;
`;

const Battlefield = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
`;

interface PlayerBoardProps {
  board: PlayerBoardType;
  playerIndex: number;
}

export const PlayerBoard = ({ board, playerIndex }: PlayerBoardProps) => (
  <BoardContainer>
    <h2>Player {playerIndex + 1} (Life: {board.life})</h2>
    
    <Zone>
      <h3>Battlefield</h3>
      <Battlefield>
        {Object.values(board.battlefield).map(card => (
          <Card 
            key={card.battlefield_id}
            name={card.card}
            tapped={card.tapped}
            damage={card.marked_damage}
          />
        ))}
      </Battlefield>
    </Zone>

    <Zone>
      <h3>Hand ({board.hand.length} cards)</h3>
      <Battlefield>
        {board.hand.map((card, i) => (
          <Card key={i} name={card} tapped={false} />
        ))}
      </Battlefield>
    </Zone>
  </BoardContainer>
);