import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { MessageSquare, Send, Inbox, Archive, User } from 'lucide-react';

const OTAMessagingHub = () => {
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [filter, setFilter] = useState('all'); // all, booking.com, airbnb, expedia
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadConversations();
  }, [filter]);

  useEffect(() => {
    if (selectedConversation) {
      loadMessages(selectedConversation.id);
    }
  }, [selectedConversation]);

  const loadConversations = async () => {
    try {
      const params = filter !== 'all' ? { ota: filter } : {};
      const response = await axios.get('/ota/conversations', { params });
      setConversations(response.data.conversations || []);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const loadMessages = async (conversationId) => {
    try {
      const response = await axios.get(`/ota/conversations/${conversationId}/messages`);
      setMessages(response.data.messages || []);
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  };

  const handleSendMessage = async () => {
    if (!newMessage.trim() || !selectedConversation) return;

    setLoading(true);
    try {
      await axios.post(`/ota/conversations/${selectedConversation.id}/messages`, {
        message: newMessage,
        channel: selectedConversation.ota_platform
      });

      toast.success('Message sent');
      setNewMessage('');
      loadMessages(selectedConversation.id);
    } catch (error) {
      toast.error('Failed to send message');
    } finally {
      setLoading(false);
    }
  };

  const getOTABadge = (ota) => {
    const colors = {
      'booking.com': 'bg-blue-100 text-blue-700',
      'airbnb': 'bg-red-100 text-red-700',
      'expedia': 'bg-yellow-100 text-yellow-700',
      'whatsapp': 'bg-green-100 text-green-700'
    };
    return colors[ota] || 'bg-gray-100 text-gray-700';
  };

  return (
    <div className="h-screen flex flex-col">
      <div className="bg-white border-b p-4">
        <h1 className="text-2xl font-bold mb-2">OTA Messaging Hub</h1>
        <div className="flex gap-2">
          <Button
            variant={filter === 'all' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('all')}
          >
            All
          </Button>
          <Button
            variant={filter === 'booking.com' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('booking.com')}
          >
            Booking.com
          </Button>
          <Button
            variant={filter === 'airbnb' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('airbnb')}
          >
            Airbnb
          </Button>
          <Button
            variant={filter === 'expedia' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('expedia')}
          >
            Expedia
          </Button>
          <Button
            variant={filter === 'whatsapp' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('whatsapp')}
          >
            WhatsApp
          </Button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Conversations List */}
        <div className="w-1/3 border-r overflow-y-auto">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              onClick={() => setSelectedConversation(conv)}
              className={`p-4 border-b cursor-pointer hover:bg-gray-50 ${
                selectedConversation?.id === conv.id ? 'bg-blue-50' : ''
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <User className="w-5 h-5 text-gray-600" />
                  <span className="font-semibold">{conv.guest_name}</span>
                </div>
                <Badge className={getOTABadge(conv.ota_platform)}>
                  {conv.ota_platform}
                </Badge>
              </div>
              <p className="text-sm text-gray-600 truncate">{conv.last_message}</p>
              <div className="flex items-center justify-between mt-2">
                <span className="text-xs text-gray-500">
                  {new Date(conv.last_message_at).toLocaleDateString()}
                </span>
                {conv.unread_count > 0 && (
                  <Badge className="bg-red-500 text-white">{conv.unread_count}</Badge>
                )}
              </div>
            </div>
          ))}

          {conversations.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              <Inbox className="w-16 h-16 mx-auto mb-4 text-gray-400" />
              No conversations
            </div>
          )}
        </div>

        {/* Messages Area */}
        <div className="flex-1 flex flex-col">
          {selectedConversation ? (
            <>
              {/* Header */}
              <div className="bg-white border-b p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="font-bold">{selectedConversation.guest_name}</h2>
                    <p className="text-sm text-gray-600">
                      Booking: {selectedConversation.booking_id?.slice(0, 8)}
                    </p>
                  </div>
                  <Badge className={getOTABadge(selectedConversation.ota_platform)}>
                    {selectedConversation.ota_platform}
                  </Badge>
                </div>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${msg.sender === 'hotel' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-md p-3 rounded-lg ${
                        msg.sender === 'hotel'
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      <p>{msg.message}</p>
                      <span className="text-xs opacity-75">
                        {new Date(msg.sent_at).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Message Input */}
              <div className="border-t p-4">
                <div className="flex gap-2">
                  <Textarea
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    placeholder="Type your message..."
                    rows={2}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSendMessage();
                      }
                    }}
                  />
                  <Button onClick={handleSendMessage} disabled={loading || !newMessage.trim()}>
                    <Send className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-500">
              <div className="text-center">
                <MessageSquare className="w-16 h-16 mx-auto mb-4 text-gray-400" />
                <p>Select a conversation to start messaging</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default OTAMessagingHub;