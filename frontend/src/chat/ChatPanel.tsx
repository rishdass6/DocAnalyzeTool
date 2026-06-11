import { useState } from "react";
import type { Message } from "./types";
import MessageInput from "./MessageInput";
import MessageList from "./MessageList";
import TypingIndicator from "./TypingIndicator";

export default function ChatPanel() {
    const [ messages, setMessages ] = useState<Message[]>([]);
    const [ aiResponse, setAiResponse ] = useState<boolean>();

    async function handleSend(text: string) {

        setMessages((prevMessages) => [
            ...prevMessages,
            { author: "user", text: `${text}`},
            { author: "ai", text: "" }
        ])

        setAiResponse(true)

        const response = await fetch("/api/chat", {
            method: "POST",
            body: JSON.stringify({ query: text }),
            headers: { "Content-Type" : "application/json"},
            credentials: "include"
        })
        
        const reader = response.body!.getReader()
        const decoder = new TextDecoder()

        while(true) {
            const { done, value } = await reader.read()
            if (done) break;

            const chunk_text = decoder.decode(value);
            //const new_text = chunk_text.replace('data: ', "")
            const new_text = chunk_text.split("\n").filter(line => line.startsWith("data: "))

            for (const line of new_text) {
                const message = line.replace("data: ", "")
                if (message === "DONE") {
                    break;
                }

                setMessages(prev => {
                    const updated = [...prev]
                    updated[updated.length - 1] = {
                        author: "ai",
                        text: updated[updated.length - 1].text + message
                    }
                    return updated 

                }
            )}
        }


        setAiResponse(false)

    }

    return (
        <div>
            <MessageInput onSend={handleSend} />
            {aiResponse && <TypingIndicator />}
            <MessageList messages={messages} />
        </div>
    )
}