import type { Message } from "./types"

interface MessageListProps {
    messages: Message[]
}

export default function MessageList({ messages }: MessageListProps) {
    return (
        <div className="flex flex-col space-y-4">
            {messages.map((message, index) => (
                <div className={`flex w-full ${message.author === "user" ? "justify-end" : "justify-start"}`}>
                    {message.author == "user" ? (
                        <p key={index} className="bg-zinc-800 p-2 self-end text-white max-w-[80%] rounded-2xl rounded-tr-none">{message.text}</p>
                    ) : (
                        <p key={index} className="self-start p-2 max-w-[95%]">{message.text}</p>
                    )}
                </div>
            ))}
        </div>
    )
}