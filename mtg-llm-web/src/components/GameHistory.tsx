import styled from '@emotion/styled'
import { HistoryStep } from '../types'

const ChatPanel = styled.div`
  background: #f5f5f5;
  padding: 15px;
  border-radius: 8px;
  height: calc(100vh - 40px);
  overflow-y: auto;
`

const ChatMessage = styled.div`
  margin-bottom: 10px;
  padding: 8px;
  background: white;
  border-radius: 4px;
  
  &:last-child {
    border-bottom: none;
  }
`

interface GameHistoryProps {
  playerHistories: HistoryStep[][]
}

export function GameHistory({ playerHistories }: GameHistoryProps) {
  return (
    <ChatPanel>
      <h2>Game History</h2>
      {playerHistories.map((playerHistory, playerIndex) => (
        playerHistory.map((step, stepIndex) => (
          <ChatMessage key={`${playerIndex}-${stepIndex}`}>
            <strong>Player {playerIndex + 1}:</strong> {step.action}
          </ChatMessage>
        ))
      ))}
    </ChatPanel>
  )
}