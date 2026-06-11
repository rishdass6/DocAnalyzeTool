import type { Message } from "./types"

interface MessageListProps {
    messages: Message[]
}

export default function MessageList({ messages }: MessageListProps) {
    return (
        <div>
            {messages.map((message, index) => (
                <div key={index}>
                    <p>{message.author}</p>
                    <p>{message.text}</p>
                </div>
            ))}
        </div>
    )
}