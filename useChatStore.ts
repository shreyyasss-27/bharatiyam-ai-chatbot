import { create } from "zustand";
import { axiosInstance } from "../lib/axios.ts";
import { toast } from "sonner";
import { pythonApi } from "../lib/axios";
import { useAuthStore } from "./useAuthStore";
/* ---------------- TYPES ---------------- */

export interface ChatMessage {
  role: "user" | "model";
  parts: { text: string }[];
}

export interface Conversation {
  _id?: string;
  title: string;
  createdAt: string;
  messages: ChatMessage[];
}

interface ChatStore {
  conversations: Conversation[];
  activeConversation: Conversation | null;

  isLoadingChats: boolean;
  isSendingMessage: boolean;
  isDeletingChat: boolean;
  isRenamingChat: boolean;
  isSearching: boolean;

  fetchChatHistory: () => Promise<void>;
  searchChats: (query: string) => Promise<void>;
  getConversation: (id: string) => Promise<void>;
  sendMessage: (message: string) => Promise<void>;
  deleteChat: (id: string) => Promise<void>;
  renameChat: (id: string, title: string) => Promise<void>;
  clearActiveChat: () => void;
  resetChatStore: () => void;
}

/* ---------------- STORE ---------------- */

export const useChatStore = create<ChatStore>((set, get) => ({

  conversations: [],
  activeConversation: {
    title: "New Chat",
    createdAt: new Date().toISOString(),
    messages: []
  },

  isLoadingChats: false,
  isSendingMessage: false,
  isDeletingChat: false,
  isRenamingChat: false,
  isSearching: false,

  /* ---------------- HISTORY ---------------- */

  fetchChatHistory: async () => {
    set({ isLoadingChats: true });
    try {
      const authUser = useAuthStore.getState().authUser;
      if (!authUser) {
        set({ conversations: [] });
        return;
      }
      const res = await pythonApi.get("/conversations", {
        params: { user_id: authUser._id }
      });
      set({ conversations: res.data.conversations || [] });
    } catch {
      toast.error("Failed to load history");
    } finally {
      set({ isLoadingChats: false });
    }
  },

  /* ---------------- SEARCH ---------------- */

  searchChats: async (query: string) => {
    if (!query.trim()) return get().fetchChatHistory();

    set({ isSearching: true });
    try {
      const res = await axiosInstance.get(`/chat/history?q=${encodeURIComponent(query)}`);
      set({ conversations: res.data });
    } catch {
      toast.error("Search failed");
    } finally {
      set({ isSearching: false });
    }
  },

  /* ---------------- LOAD CHAT ---------------- */

  getConversation: async (id: string) => {
    try {
      if(id === "") return;
      const authUser = useAuthStore.getState().authUser;
      if (!authUser) {
        toast.error("Please sign in to view chat");
        return;
      }
      const res = await pythonApi.get("/history", {
        params: { session_id: id, user_id: authUser._id }
      });
      const messages = res.data.history || [];
      set({ 
        activeConversation: {
          _id: id,
          title: `Chat ${id.slice(0, 8)}`,
          createdAt: new Date().toISOString(),
          messages: messages.map((msg: any) => ({
            role: msg.role === "user" ? "user" : "model",
            parts: [{ text: msg.text }]
          }))
        }
      });
    } catch {
      toast.error("Failed to open chat");
    }
  },

  /* ---------------- SEND MESSAGE ---------------- */

  sendMessage: async (message: string) => {

    if (!message.trim()) return;
    const state = get();
    const sessionId = state.activeConversation?._id;
    const authUser = useAuthStore.getState().authUser;
    if (!authUser) {
      toast.error("Please sign in to send messages");
      return;
    }

    // Optimistic User Message
    const optimisticMessage: ChatMessage = {
      role: "user",
      parts: [{ text: message }]
    };

    set(state => ({
      activeConversation: {
        _id: state.activeConversation?._id,
        title: state.activeConversation?.title || "New Chat",
        createdAt: state.activeConversation?.createdAt || new Date().toISOString(),
        messages: [...(state.activeConversation?.messages || []), optimisticMessage]
      }
    }));

    set({ isSendingMessage: true });

    try {
      const res = await pythonApi.post("/query", {
        query: message,
        session_id: sessionId,
        return_history: true,
        user_id: authUser._id,
      });

      const aiMessage: ChatMessage = {
        role: "model",
        parts: [{ text: res.data.response }]
      };

      set(state => ({
        activeConversation: {
          ...state.activeConversation!,
          _id: res.data.session_id || state.activeConversation?._id,
          messages: [...state.activeConversation!.messages, aiMessage]
        }
      }));

      // No sidebar refresh needed for stateless API

    } catch {
      set(state => ({
        activeConversation: {
          ...state.activeConversation!,
          messages: state.activeConversation!.messages.slice(0, -1)
        }
      }));
      toast.error("Message failed");
    } finally {
      set({ isSendingMessage: false });
    }
  },

  /* ---------------- DELETE CHAT ---------------- */

  deleteChat: async (id: string) => {
    set({ isDeletingChat: true });

    try {
      const authUser = useAuthStore.getState().authUser;
      if (!authUser) {
        toast.error("Please sign in to delete chat");
        return;
      }
      await pythonApi.delete("/history", {
        params: { session_id: id, user_id: authUser._id }
      });

      set(state => ({
        conversations: state.conversations.filter(c => c._id !== id),
        activeConversation:
          state.activeConversation?._id === id
            ? {
              title: "New Chat",
              createdAt: new Date().toISOString(),
              messages: []
            }
            : state.activeConversation
      }));

      toast.success("Chat deleted");

    } catch {
      toast.error("Delete failed");
    } finally {
      set({ isDeletingChat: false });
    }
  },

  /* ---------------- RENAME CHAT ---------------- */

  renameChat: async (id: string, title: string) => {
    if (!title.trim()) return;

    set({ isRenamingChat: true });

    try {
      const res = await axiosInstance.patch(`/chat/${id}`, { title });

      set(state => ({
        conversations: state.conversations.map(chat =>
          chat._id === id ? { ...chat, title: res.data.title } : chat
        ),
        activeConversation:
          state.activeConversation?._id === id
            ? { ...state.activeConversation, title: res.data.title }
            : state.activeConversation
      }));

      toast.success("Chat renamed");

    } catch {
      toast.error("Rename failed");
    } finally {
      set({ isRenamingChat: false });
    }
  },

  /* ---------------- HELPERS ---------------- */

  clearActiveChat: () => set({
    activeConversation: {
      title: "New Chat",
      createdAt: new Date().toISOString(),
      messages: []
    }
  }),

  resetChatStore: () => set({
    conversations: [],
    activeConversation: {
      title: "New Chat",
      createdAt: new Date().toISOString(),
      messages: []
    },
    isLoadingChats: false,
    isSendingMessage: false,
    isDeletingChat: false,
    isRenamingChat: false,
    isSearching: false
  })

}));
