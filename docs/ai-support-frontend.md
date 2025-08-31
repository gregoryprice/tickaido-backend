name: "AI Support Frontend - Complete Implementation PRP"
description: |

## Purpose
Comprehensive PRP for implementing a complete React frontend for AI Ticket Creator Chrome extension with modern UI components, real-time updates, file handling, and third-party integrations dashboard.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Progressive Success**: Start simple, test and validate with actual API calls and test cases, then enhance
4. **Global rules**: You must follow all rules in CLAUDE.md

---

## Goal
Build a production-ready React frontend application for the AI Ticket Creator system that provides comprehensive ticket management UI, real-time notifications, file upload/preview capabilities, AI configuration management, and third-party integrations dashboard.

## Why
- **User Experience**: Provide intuitive, modern interface for ticket management
- **Real-time Updates**: Show live ticket status and processing updates via WebSocket
- **AI Configuration**: Allow dynamic configuration of AI agents and prompts
- **File Management**: Handle all file types with preview and processing status
- **Integration Management**: Manage third-party service connections and settings
- **Analytics Dashboard**: Visualize ticket metrics and system health

## What
A React frontend application with:
- **Modern React 18+ with TypeScript** for type safety and performance
- **Ticket management interface** with CRUD operations and AI-powered categorization
- **Real-time WebSocket connection** for live updates and notifications
- **File upload system** with drag-drop, preview, and processing status
- **AI configuration dashboard** for managing agent prompts and settings
- **Third-party integrations panel** for Salesforce, Jira, Zendesk, GitHub, Slack, Teams
- **Analytics dashboard** with charts and metrics visualization
- **Responsive design** with mobile-first approach
- **Accessibility compliance** (WCAG 2.1 AA)
- **Progressive Web App** capabilities for Chrome extension integration

### Success Criteria
- [ ] All components have TypeScript interfaces and proper typing
- [ ] Complete test suite with 90%+ coverage using Jest and React Testing Library
- [ ] Real-time WebSocket connection with reconnection logic
- [ ] File upload with progress indicators and error handling
- [ ] AI configuration UI with live preview of prompt changes
- [ ] Third-party integration status dashboard
- [ ] Responsive design tested on mobile and desktop
- [ ] Accessibility compliance verified with automated tools
- [ ] PWA functionality with service worker and offline capability
- [ ] Chrome extension messaging integration

## All Needed Context

### Documentation & References (list all context needed to implement the feature)
```yaml
# MUST READ - Include these in your context window
- url: https://react.dev/learn
  why: React 18+ fundamentals, hooks, concurrent features, and best practices
  
- url: https://www.typescriptlang.org/docs/
  why: TypeScript fundamentals for React component typing
  
- url: https://tailwindcss.com/docs
  why: Modern utility-first CSS framework for responsive design
  
- url: https://ui.shadcn.com/docs
  why: Modern React component library built on Radix UI and Tailwind
  
- url: https://tanstack.com/query/latest/docs/framework/react/overview
  why: Data fetching, caching, and synchronization for API calls
  
- url: https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API
  section: WebSocket client implementation
  critical: Real-time updates and notification system
  
- url: https://recharts.org/en-US/guide
  why: Data visualization for analytics dashboard
  
- url: https://react-hook-form.com/get-started
  why: Form handling with validation for ticket creation and AI config
  
- url: https://testing-library.com/docs/react-testing-library/intro/
  why: Component testing patterns and best practices
  
- url: https://developer.chrome.com/docs/extensions/mv3/messaging/
  section: Chrome extension messaging
  critical: Integration with Chrome extension
```

### Current Frontend Architecture
```bash
frontend/
├── src/
│   ├── components/           # Reusable UI components
│   │   ├── ui/              # Base UI components (Button, Input, etc.)
│   │   ├── forms/           # Form components (TicketForm, ConfigForm)
│   │   ├── layout/          # Layout components (Header, Sidebar, Nav)
│   │   └── charts/          # Chart components for analytics
│   ├── pages/               # Route-level page components
│   │   ├── Dashboard.tsx    # Main dashboard with ticket overview
│   │   ├── Tickets.tsx      # Ticket management interface
│   │   ├── Analytics.tsx    # Analytics and reporting dashboard
│   │   ├── Integrations.tsx # Third-party integrations management
│   │   └── Settings.tsx     # AI configuration and app settings
│   ├── hooks/               # Custom React hooks
│   │   ├── useWebSocket.ts  # WebSocket connection management
│   │   ├── useFileUpload.ts # File upload handling
│   │   ├── useApi.ts        # API client wrapper
│   │   └── useAuth.ts       # Authentication state management
│   ├── services/            # API services and utilities
│   │   ├── api.ts           # Main API client
│   │   ├── websocket.ts     # WebSocket client
│   │   ├── fileUpload.ts    # File upload service
│   │   └── chrome.ts        # Chrome extension messaging
│   ├── types/               # TypeScript type definitions
│   │   ├── ticket.ts        # Ticket-related types
│   │   ├── integration.ts   # Integration types
│   │   ├── api.ts           # API response types
│   │   └── websocket.ts     # WebSocket message types
│   ├── stores/              # State management (Zustand)
│   │   ├── ticketStore.ts   # Ticket state management
│   │   ├── authStore.ts     # Authentication state
│   │   ├── configStore.ts   # AI configuration state
│   │   └── uiStore.ts       # UI state (modals, notifications)
│   ├── utils/               # Utility functions
│   │   ├── validation.ts    # Form validation schemas
│   │   ├── formatters.ts    # Data formatting utilities
│   │   └── constants.ts     # App constants and enums
│   └── assets/              # Static assets
│       ├── icons/           # SVG icons
│       └── images/          # Images and logos
├── public/
│   ├── manifest.json        # PWA manifest
│   └── service-worker.js    # Service worker for PWA
├── package.json
├── tsconfig.json
├── tailwind.config.js
├── vite.config.ts
└── jest.config.js
```

## Implementation Blueprint

### Core Technology Stack
```yaml
FRAMEWORK: React 18.2.0+
LANGUAGE: TypeScript 5.0+
STYLING: TailwindCSS 3.3+ with shadcn/ui components
STATE_MANAGEMENT: Zustand 4.4+ (lightweight, TypeScript-first)
DATA_FETCHING: TanStack Query 4.0+ (React Query)
FORMS: React Hook Form 7.45+ with Zod validation
TESTING: Jest 29+ with React Testing Library
BUILD_TOOL: Vite 4.0+ for fast development and building
CHARTS: Recharts 2.7+ for analytics visualization
WEBSOCKET: Native WebSocket API with reconnection logic
PWA: Workbox for service worker and offline functionality
```

### Component Architecture

#### Base UI Components (shadcn/ui pattern)
```typescript
// src/components/ui/button.tsx
import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
```

#### Ticket Management Components
```typescript
// src/components/tickets/TicketCard.tsx
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Ticket, TicketPriority, TicketStatus } from "@/types/ticket"
import { formatDistanceToNow } from "date-fns"
import { ExternalLink, MessageCircle, Paperclip } from "lucide-react"

interface TicketCardProps {
  ticket: Ticket
  onEdit: (ticket: Ticket) => void
  onView: (ticket: Ticket) => void
}

export function TicketCard({ ticket, onEdit, onView }: TicketCardProps) {
  const getPriorityColor = (priority: TicketPriority) => {
    switch (priority) {
      case "high": return "destructive"
      case "medium": return "default"
      case "low": return "secondary"
      default: return "secondary"
    }
  }

  const getStatusColor = (status: TicketStatus) => {
    switch (status) {
      case "open": return "default"
      case "in_progress": return "secondary"
      case "resolved": return "outline"
      case "closed": return "secondary"
      default: return "secondary"
    }
  }

  return (
    <Card className="hover:shadow-md transition-shadow cursor-pointer" onClick={() => onView(ticket)}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="space-y-1 flex-1">
            <CardTitle className="text-base line-clamp-2">{ticket.title}</CardTitle>
            <CardDescription className="line-clamp-2">{ticket.description}</CardDescription>
          </div>
          <div className="flex gap-1 ml-2">
            <Badge variant={getPriorityColor(ticket.priority)}>{ticket.priority}</Badge>
            <Badge variant={getStatusColor(ticket.status)}>{ticket.status}</Badge>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="pt-0">
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <div className="flex items-center gap-4">
            <span>#{ticket.id}</span>
            {ticket.attachments && ticket.attachments.length > 0 && (
              <div className="flex items-center gap-1">
                <Paperclip className="h-3 w-3" />
                <span>{ticket.attachments.length}</span>
              </div>
            )}
            {ticket.comments_count && ticket.comments_count > 0 && (
              <div className="flex items-center gap-1">
                <MessageCircle className="h-3 w-3" />
                <span>{ticket.comments_count}</span>
              </div>
            )}
          </div>
          
          <div className="flex items-center gap-2">
            {ticket.integration_url && (
              <ExternalLink className="h-3 w-3" />
            )}
            <span>{formatDistanceToNow(new Date(ticket.created_at), { addSuffix: true })}</span>
          </div>
        </div>
        
        <div className="flex justify-end gap-2 mt-3">
          <Button 
            variant="outline" 
            size="sm" 
            onClick={(e) => {
              e.stopPropagation()
              onEdit(ticket)
            }}
          >
            Edit
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
```

#### File Upload Component with Progress
```typescript
// src/components/files/FileUpload.tsx
import { useState, useCallback, useRef } from "react"
import { useDropzone } from "react-dropzone"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { X, Upload, File, Image, Video, Music, FileText } from "lucide-react"
import { useFileUpload } from "@/hooks/useFileUpload"
import { cn } from "@/lib/utils"

interface FileUploadProps {
  ticketId?: number
  onUploadComplete?: (files: UploadedFile[]) => void
  maxFiles?: number
  maxSizeBytes?: number
  acceptedFileTypes?: string[]
}

interface UploadedFile {
  id: string
  name: string
  size: number
  type: string
  url: string
  processing_status: "pending" | "processing" | "completed" | "failed"
  analysis_result?: {
    extracted_text?: string
    confidence?: number
    analysis_type: "transcription" | "ocr" | "metadata"
  }
}

export function FileUpload({ 
  ticketId, 
  onUploadComplete, 
  maxFiles = 10,
  maxSizeBytes = 100 * 1024 * 1024, // 100MB
  acceptedFileTypes = [] 
}: FileUploadProps) {
  const [files, setFiles] = useState<File[]>([])
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([])
  const [error, setError] = useState<string | null>(null)
  
  const { uploadFiles, uploadProgress, isUploading } = useFileUpload()

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    setError(null)
    
    if (rejectedFiles.length > 0) {
      const errorMessages = rejectedFiles.map(file => 
        `${file.file.name}: ${file.errors.map((e: any) => e.message).join(", ")}`
      )
      setError(`Some files were rejected: ${errorMessages.join("; ")}`)
    }

    if (files.length + acceptedFiles.length > maxFiles) {
      setError(`Maximum ${maxFiles} files allowed`)
      return
    }

    setFiles(prev => [...prev, ...acceptedFiles])
  }, [files.length, maxFiles])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    maxSize: maxSizeBytes,
    accept: acceptedFileTypes.length > 0 ? 
      Object.fromEntries(acceptedFileTypes.map(type => [type, []])) : 
      undefined
  })

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleUpload = async () => {
    if (files.length === 0) return

    try {
      setError(null)
      const results = await uploadFiles(files, ticketId)
      setUploadedFiles(prev => [...prev, ...results])
      setFiles([])
      onUploadComplete?.(results)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed")
    }
  }

  const getFileIcon = (fileType: string) => {
    if (fileType.startsWith('image/')) return <Image className="h-4 w-4" />
    if (fileType.startsWith('video/')) return <Video className="h-4 w-4" />
    if (fileType.startsWith('audio/')) return <Music className="h-4 w-4" />
    if (fileType.includes('pdf') || fileType.includes('document')) return <FileText className="h-4 w-4" />
    return <File className="h-4 w-4" />
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  return (
    <div className="space-y-4">
      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={cn(
          "border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors",
          isDragActive ? "border-primary bg-primary/5" : "border-muted-foreground/25",
          isUploading && "pointer-events-none opacity-50"
        )}
      >
        <input {...getInputProps()} />
        <Upload className="h-10 w-10 mx-auto mb-4 text-muted-foreground" />
        {isDragActive ? (
          <p className="text-lg">Drop files here...</p>
        ) : (
          <div>
            <p className="text-lg mb-2">Drag & drop files here, or click to select</p>
            <p className="text-sm text-muted-foreground">
              Maximum {maxFiles} files, {formatFileSize(maxSizeBytes)} per file
            </p>
          </div>
        )}
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* File List */}
      {files.length > 0 && (
        <div className="space-y-2">
          <h4 className="font-medium">Files to upload:</h4>
          {files.map((file, index) => (
            <div key={`${file.name}-${index}`} className="flex items-center gap-2 p-2 border rounded">
              {getFileIcon(file.type)}
              <span className="flex-1 truncate">{file.name}</span>
              <Badge variant="secondary">{formatFileSize(file.size)}</Badge>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => removeFile(index)}
                disabled={isUploading}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Upload Progress */}
      {isUploading && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Uploading files...</span>
            <span className="text-sm text-muted-foreground">{Math.round(uploadProgress)}%</span>
          </div>
          <Progress value={uploadProgress} />
        </div>
      )}

      {/* Upload Button */}
      {files.length > 0 && !isUploading && (
        <Button onClick={handleUpload} className="w-full">
          Upload {files.length} file{files.length !== 1 ? 's' : ''}
        </Button>
      )}

      {/* Uploaded Files */}
      {uploadedFiles.length > 0 && (
        <div className="space-y-2">
          <h4 className="font-medium">Uploaded files:</h4>
          {uploadedFiles.map((file) => (
            <div key={file.id} className="flex items-center gap-2 p-2 border rounded bg-muted/30">
              {getFileIcon(file.type)}
              <span className="flex-1 truncate">{file.name}</span>
              <Badge variant={
                file.processing_status === "completed" ? "default" :
                file.processing_status === "failed" ? "destructive" :
                file.processing_status === "processing" ? "secondary" : "outline"
              }>
                {file.processing_status}
              </Badge>
              {file.analysis_result && (
                <Badge variant="outline" className="text-xs">
                  {file.analysis_result.analysis_type}
                </Badge>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

### WebSocket Integration

#### WebSocket Hook
```typescript
// src/hooks/useWebSocket.ts
import { useEffect, useRef, useState, useCallback } from "react"
import { useAuthStore } from "@/stores/authStore"
import { WebSocketMessage, WebSocketMessageType } from "@/types/websocket"

interface UseWebSocketOptions {
  reconnectAttempts?: number
  reconnectInterval?: number
  onMessage?: (message: WebSocketMessage) => void
  onError?: (error: Event) => void
  onConnect?: () => void
  onDisconnect?: () => void
}

interface UseWebSocketReturn {
  isConnected: boolean
  lastMessage: WebSocketMessage | null
  sendMessage: (message: WebSocketMessage) => void
  disconnect: () => void
  reconnect: () => void
}

export function useWebSocket(
  url: string,
  options: UseWebSocketOptions = {}
): UseWebSocketReturn {
  const {
    reconnectAttempts = 5,
    reconnectInterval = 3000,
    onMessage,
    onError,
    onConnect,
    onDisconnect
  } = options

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
  const reconnectCountRef = useRef(0)
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  
  const { token } = useAuthStore()

  const connect = useCallback(() => {
    try {
      const wsUrl = new URL(url)
      if (token) {
        wsUrl.searchParams.set('token', token)
      }

      wsRef.current = new WebSocket(wsUrl.toString())

      wsRef.current.onopen = () => {
        setIsConnected(true)
        reconnectCountRef.current = 0
        onConnect?.()
      }

      wsRef.current.onclose = (event) => {
        setIsConnected(false)
        onDisconnect?.()

        // Auto-reconnect if not closed intentionally
        if (event.code !== 1000 && reconnectCountRef.current < reconnectAttempts) {
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectCountRef.current++
            connect()
          }, reconnectInterval * Math.pow(1.5, reconnectCountRef.current))
        }
      }

      wsRef.current.onerror = (error) => {
        onError?.(error)
      }

      wsRef.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          setLastMessage(message)
          onMessage?.(message)
        } catch (err) {
          console.error("Failed to parse WebSocket message:", err)
        }
      }
    } catch (error) {
      console.error("Failed to connect WebSocket:", error)
    }
  }, [url, token, onMessage, onError, onConnect, onDisconnect, reconnectAttempts, reconnectInterval])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    reconnectCountRef.current = reconnectAttempts // Prevent auto-reconnect
    wsRef.current?.close(1000, "Intentional disconnect")
  }, [reconnectAttempts])

  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    } else {
      console.warn("WebSocket is not connected")
    }
  }, [])

  const reconnect = useCallback(() => {
    disconnect()
    reconnectCountRef.current = 0
    setTimeout(connect, 100)
  }, [disconnect, connect])

  useEffect(() => {
    connect()
    return disconnect
  }, [connect, disconnect])

  return {
    isConnected,
    lastMessage,
    sendMessage,
    disconnect,
    reconnect
  }
}
```

#### Real-time Notifications Component
```typescript
// src/components/notifications/NotificationCenter.tsx
import { useEffect, useState } from "react"
import { Bell, X, CheckCircle, AlertCircle, Info, Upload } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { useWebSocket } from "@/hooks/useWebSocket"
import { WebSocketMessage, NotificationType } from "@/types/websocket"
import { formatDistanceToNow } from "date-fns"

interface Notification {
  id: string
  type: NotificationType
  title: string
  message: string
  timestamp: Date
  read: boolean
  actionUrl?: string
}

export function NotificationCenter() {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [isOpen, setIsOpen] = useState(false)

  const { lastMessage } = useWebSocket(
    `${import.meta.env.VITE_WS_URL}/notifications`,
    {
      onMessage: handleWebSocketMessage
    }
  )

  function handleWebSocketMessage(message: WebSocketMessage) {
    if (message.type === "notification") {
      const notification: Notification = {
        id: crypto.randomUUID(),
        type: message.data.type,
        title: message.data.title,
        message: message.data.message,
        timestamp: new Date(message.timestamp),
        read: false,
        actionUrl: message.data.action_url
      }
      
      setNotifications(prev => [notification, ...prev.slice(0, 49)]) // Keep max 50
      
      // Show browser notification if permitted
      if (Notification.permission === "granted") {
        new Notification(notification.title, {
          body: notification.message,
          icon: "/favicon.ico",
          tag: notification.id
        })
      }
    }
  }

  const unreadCount = notifications.filter(n => !n.read).length

  const markAsRead = (notificationId: string) => {
    setNotifications(prev => 
      prev.map(n => n.id === notificationId ? { ...n, read: true } : n)
    )
  }

  const markAllAsRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })))
  }

  const removeNotification = (notificationId: string) => {
    setNotifications(prev => prev.filter(n => n.id !== notificationId))
  }

  const getIcon = (type: NotificationType) => {
    switch (type) {
      case "success": return <CheckCircle className="h-4 w-4 text-green-500" />
      case "error": return <AlertCircle className="h-4 w-4 text-red-500" />
      case "warning": return <AlertCircle className="h-4 w-4 text-yellow-500" />
      case "info": return <Info className="h-4 w-4 text-blue-500" />
      case "file_processing": return <Upload className="h-4 w-4 text-blue-500" />
      default: return <Info className="h-4 w-4 text-gray-500" />
    }
  }

  // Request notification permission on mount
  useEffect(() => {
    if (Notification.permission === "default") {
      Notification.requestPermission()
    }
  }, [])

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <Badge 
              variant="destructive" 
              className="absolute -top-1 -right-1 h-5 w-5 rounded-full p-0 flex items-center justify-center text-xs"
            >
              {unreadCount > 99 ? "99+" : unreadCount}
            </Badge>
          )}
        </Button>
      </PopoverTrigger>
      
      <PopoverContent className="w-96 p-0" align="end">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="font-semibold">Notifications</h3>
          {unreadCount > 0 && (
            <Button variant="ghost" size="sm" onClick={markAllAsRead}>
              Mark all as read
            </Button>
          )}
        </div>
        
        {notifications.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            <Bell className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>No notifications yet</p>
          </div>
        ) : (
          <ScrollArea className="h-96">
            <div className="space-y-1 p-2">
              {notifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`flex gap-3 p-3 rounded-md hover:bg-muted/50 ${
                    !notification.read ? "bg-muted/30" : ""
                  }`}
                  onClick={() => markAsRead(notification.id)}
                >
                  {getIcon(notification.type)}
                  
                  <div className="flex-1 space-y-1">
                    <div className="flex items-start justify-between">
                      <h4 className="text-sm font-medium leading-none">
                        {notification.title}
                      </h4>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 opacity-50 hover:opacity-100"
                        onClick={(e) => {
                          e.stopPropagation()
                          removeNotification(notification.id)
                        }}
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </div>
                    
                    <p className="text-sm text-muted-foreground leading-snug">
                      {notification.message}
                    </p>
                    
                    <p className="text-xs text-muted-foreground">
                      {formatDistanceToNow(notification.timestamp, { addSuffix: true })}
                    </p>
                    
                    {notification.actionUrl && (
                      <Button variant="outline" size="sm" asChild>
                        <a href={notification.actionUrl} target="_blank" rel="noopener noreferrer">
                          View Details
                        </a>
                      </Button>
                    )}
                  </div>
                  
                  {!notification.read && (
                    <div className="w-2 h-2 rounded-full bg-blue-500 mt-2" />
                  )}
                </div>
              ))}
            </div>
          </ScrollArea>
        )}
      </PopoverContent>
    </Popover>
  )
}
```

### AI Configuration Management Interface

```typescript
// src/pages/Settings.tsx - AI Configuration Management
import { useState, useEffect } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Save, RefreshCw, Eye, TestTube } from "lucide-react"
import { useApi } from "@/hooks/useApi"
import { toast } from "sonner"

const aiConfigSchema = z.object({
  model: z.string().min(1, "Model is required"),
  temperature: z.number().min(0).max(2),
  max_tokens: z.number().min(1).max(8000),
  system_prompt: z.string().min(10, "System prompt must be at least 10 characters"),
  tools_enabled: z.array(z.string()),
  timeout: z.number().min(5).max(300)
})

type AIConfigFormData = z.infer<typeof aiConfigSchema>

interface AIAgentConfig {
  agent_type: string
  model: string
  temperature: number
  max_tokens: number
  system_prompt: string
  tools_enabled: string[]
  timeout: number
  updated_at: string
  version: number
}

const AVAILABLE_MODELS = [
  "gpt-4o",
  "gpt-4o-mini", 
  "claude-3-5-sonnet-20241022",
  "claude-3-haiku-20240307"
]

const AVAILABLE_TOOLS = [
  "analyze_file",
  "create_ticket", 
  "search_knowledge_base",
  "categorize_issue",
  "create_jira_ticket",
  "create_salesforce_case",
  "create_github_issue"
]

const AGENT_TYPES = [
  {
    id: "customer_support_agent",
    name: "Customer Support Agent",
    description: "Main agent for creating and managing support tickets"
  },
  {
    id: "categorization_agent", 
    name: "Categorization Agent",
    description: "Agent for auto-categorizing and prioritizing tickets"
  },
  {
    id: "file_analysis_agent",
    name: "File Analysis Agent", 
    description: "Agent for processing and analyzing uploaded files"
  }
]

export function Settings() {
  const [selectedAgent, setSelectedAgent] = useState("customer_support_agent")
  const [config, setConfig] = useState<AIAgentConfig | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isTesting, setIsTesting] = useState(false)
  const [testResult, setTestResult] = useState<any>(null)
  
  const { get, put, post } = useApi()

  const form = useForm<AIConfigFormData>({
    resolver: zodResolver(aiConfigSchema),
    defaultValues: {
      model: "gpt-4o-mini",
      temperature: 0.2,
      max_tokens: 2000,
      system_prompt: "",
      tools_enabled: [],
      timeout: 30
    }
  })

  // Load configuration for selected agent
  useEffect(() => {
    loadConfig()
  }, [selectedAgent])

  const loadConfig = async () => {
    setIsLoading(true)
    try {
      const response = await get<AIAgentConfig>(`/ai-config/${selectedAgent}`)
      setConfig(response.data)
      form.reset({
        model: response.data.model,
        temperature: response.data.temperature,
        max_tokens: response.data.max_tokens,
        system_prompt: response.data.system_prompt,
        tools_enabled: response.data.tools_enabled,
        timeout: response.data.timeout
      })
    } catch (error) {
      toast.error(`Failed to load configuration: ${error}`)
    } finally {
      setIsLoading(false)
    }
  }

  const onSubmit = async (data: AIConfigFormData) => {
    setIsLoading(true)
    try {
      const response = await put(`/ai-config/${selectedAgent}`, data)
      setConfig(response.data)
      toast.success("Configuration updated successfully")
    } catch (error) {
      toast.error(`Failed to update configuration: ${error}`)
    } finally {
      setIsLoading(false)
    }
  }

  const testConfiguration = async () => {
    setIsTesting(true)
    setTestResult(null)
    
    try {
      const testData = {
        agent_type: selectedAgent,
        test_input: "Test ticket creation with current configuration",
        config_override: form.getValues()
      }
      
      const response = await post("/ai-config/test", testData)
      setTestResult(response.data)
      toast.success("Configuration test completed")
    } catch (error) {
      toast.error(`Configuration test failed: ${error}`)
      setTestResult({ error: error })
    } finally {
      setIsTesting(false)
    }
  }

  return (
    <div className="container mx-auto p-6 max-w-4xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold">AI Configuration</h1>
        <p className="text-muted-foreground">
          Configure AI agents, prompts, and model parameters
        </p>
      </div>

      <Tabs value={selectedAgent} onValueChange={setSelectedAgent}>
        <TabsList className="grid w-full grid-cols-3">
          {AGENT_TYPES.map((agent) => (
            <TabsTrigger key={agent.id} value={agent.id}>
              {agent.name}
            </TabsTrigger>
          ))}
        </TabsList>

        {AGENT_TYPES.map((agent) => (
          <TabsContent key={agent.id} value={agent.id}>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  {agent.name}
                  {config && (
                    <Badge variant="outline">
                      v{config.version} • {new Date(config.updated_at).toLocaleDateString()}
                    </Badge>
                  )}
                </CardTitle>
                <CardDescription>{agent.description}</CardDescription>
              </CardHeader>

              <CardContent>
                <Form {...form}>
                  <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <FormField
                        control={form.control}
                        name="model"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Model</FormLabel>
                            <Select onValueChange={field.onChange} defaultValue={field.value}>
                              <FormControl>
                                <SelectTrigger>
                                  <SelectValue placeholder="Select a model" />
                                </SelectTrigger>
                              </FormControl>
                              <SelectContent>
                                {AVAILABLE_MODELS.map((model) => (
                                  <SelectItem key={model} value={model}>
                                    {model}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                            <FormMessage />
                          </FormItem>
                        )}
                      />

                      <FormField
                        control={form.control}
                        name="temperature"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Temperature</FormLabel>
                            <FormControl>
                              <Input
                                type="number"
                                step="0.1"
                                min="0"
                                max="2"
                                {...field}
                                onChange={e => field.onChange(parseFloat(e.target.value))}
                              />
                            </FormControl>
                            <FormDescription>
                              Controls randomness (0 = deterministic, 2 = very random)
                            </FormDescription>
                            <FormMessage />
                          </FormItem>
                        )}
                      />

                      <FormField
                        control={form.control}
                        name="max_tokens"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Max Tokens</FormLabel>
                            <FormControl>
                              <Input
                                type="number"
                                min="1"
                                max="8000"
                                {...field}
                                onChange={e => field.onChange(parseInt(e.target.value))}
                              />
                            </FormControl>
                            <FormDescription>
                              Maximum response length
                            </FormDescription>
                            <FormMessage />
                          </FormItem>
                        )}
                      />

                      <FormField
                        control={form.control}
                        name="timeout"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Timeout (seconds)</FormLabel>
                            <FormControl>
                              <Input
                                type="number"
                                min="5"
                                max="300"
                                {...field}
                                onChange={e => field.onChange(parseInt(e.target.value))}
                              />
                            </FormControl>
                            <FormDescription>
                              Request timeout in seconds
                            </FormDescription>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    </div>

                    <FormField
                      control={form.control}
                      name="system_prompt"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>System Prompt</FormLabel>
                          <FormControl>
                            <Textarea
                              rows={10}
                              placeholder="Enter the system prompt for this agent..."
                              {...field}
                            />
                          </FormControl>
                          <FormDescription>
                            The main instructions for how this agent should behave
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="tools_enabled"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Enabled Tools</FormLabel>
                          <FormDescription>
                            Select which tools this agent can use
                          </FormDescription>
                          <div className="grid grid-cols-2 gap-2 mt-2">
                            {AVAILABLE_TOOLS.map((tool) => (
                              <FormItem key={tool} className="flex items-center space-x-2">
                                <FormControl>
                                  <Switch
                                    checked={field.value.includes(tool)}
                                    onCheckedChange={(checked) => {
                                      if (checked) {
                                        field.onChange([...field.value, tool])
                                      } else {
                                        field.onChange(field.value.filter(t => t !== tool))
                                      }
                                    }}
                                  />
                                </FormControl>
                                <FormLabel className="text-sm font-normal">
                                  {tool.replace(/_/g, ' ')}
                                </FormLabel>
                              </FormItem>
                            ))}
                          </div>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    {testResult && (
                      <Alert className={testResult.error ? "border-destructive" : "border-green-500"}>
                        <AlertDescription>
                          {testResult.error ? (
                            <span className="text-destructive">Test failed: {testResult.error}</span>
                          ) : (
                            <div className="space-y-2">
                              <span className="text-green-600 font-medium">Test passed!</span>
                              <pre className="text-xs bg-muted p-2 rounded mt-2 overflow-x-auto">
                                {JSON.stringify(testResult, null, 2)}
                              </pre>
                            </div>
                          )}
                        </AlertDescription>
                      </Alert>
                    )}

                    <div className="flex gap-2">
                      <Button 
                        type="submit" 
                        disabled={isLoading}
                        className="flex items-center gap-2"
                      >
                        {isLoading ? (
                          <RefreshCw className="h-4 w-4 animate-spin" />
                        ) : (
                          <Save className="h-4 w-4" />
                        )}
                        Save Configuration
                      </Button>

                      <Button
                        type="button"
                        variant="outline"
                        onClick={testConfiguration}
                        disabled={isTesting}
                        className="flex items-center gap-2"
                      >
                        {isTesting ? (
                          <RefreshCw className="h-4 w-4 animate-spin" />
                        ) : (
                          <TestTube className="h-4 w-4" />
                        )}
                        Test Configuration
                      </Button>

                      <Button
                        type="button"
                        variant="outline"
                        onClick={loadConfig}
                        disabled={isLoading}
                        className="flex items-center gap-2"
                      >
                        <RefreshCw className="h-4 w-4" />
                        Reset
                      </Button>
                    </div>
                  </form>
                </Form>
              </CardContent>
            </Card>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  )
}
```

### Analytics Dashboard

```typescript
// src/pages/Analytics.tsx - Analytics Dashboard with Charts
import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { 
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, 
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer 
} from "recharts"
import { 
  TrendingUp, TrendingDown, Clock, CheckCircle, 
  AlertTriangle, Users, FileText, Zap 
} from "lucide-react"
import { useApi } from "@/hooks/useApi"

interface AnalyticsData {
  overview: {
    total_tickets: number
    open_tickets: number
    resolved_tickets: number
    avg_resolution_time: number
    tickets_today: number
    resolution_rate: number
  }
  ticket_trends: Array<{
    date: string
    created: number
    resolved: number
    open: number
  }>
  category_distribution: Array<{
    category: string
    count: number
    percentage: number
  }>
  priority_breakdown: Array<{
    priority: string
    count: number
    avg_resolution_hours: number
  }>
  integration_usage: Array<{
    integration: string
    tickets_created: number
    success_rate: number
  }>
  ai_performance: {
    categorization_accuracy: number
    processing_time_avg: number
    files_processed: number
    transcription_success_rate: number
  }
}

const COLORS = {
  primary: "#3b82f6",
  success: "#10b981", 
  warning: "#f59e0b",
  danger: "#ef4444",
  secondary: "#6b7280"
}

export function Analytics() {
  const [data, setData] = useState<AnalyticsData | null>(null)
  const [timeRange, setTimeRange] = useState("7d")
  const [isLoading, setIsLoading] = useState(true)
  
  const { get } = useApi()

  useEffect(() => {
    loadAnalytics()
  }, [timeRange])

  const loadAnalytics = async () => {
    setIsLoading(true)
    try {
      const response = await get<AnalyticsData>(`/analytics?period=${timeRange}`)
      setData(response.data)
    } catch (error) {
      console.error("Failed to load analytics:", error)
    } finally {
      setIsLoading(false)
    }
  }

  if (isLoading || !data) {
    return (
      <div className="container mx-auto p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Analytics Dashboard</h1>
          <p className="text-muted-foreground">
            Monitor ticket performance and system health
          </p>
        </div>
        
        <div className="flex gap-2">
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="24h">Last 24h</SelectItem>
              <SelectItem value="7d">Last 7 days</SelectItem>
              <SelectItem value="30d">Last 30 days</SelectItem>
              <SelectItem value="90d">Last 90 days</SelectItem>
            </SelectContent>
          </Select>
          
          <Button variant="outline" onClick={loadAnalytics}>
            Refresh
          </Button>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Tickets</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.overview.total_tickets}</div>
            <p className="text-xs text-muted-foreground">
              {data.overview.tickets_today} created today
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Open Tickets</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.overview.open_tickets}</div>
            <div className="flex items-center gap-1 text-xs">
              {data.overview.open_tickets > data.overview.resolved_tickets ? (
                <TrendingUp className="h-3 w-3 text-red-500" />
              ) : (
                <TrendingDown className="h-3 w-3 text-green-500" />
              )}
              <span className="text-muted-foreground">vs resolved</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Resolution Rate</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.overview.resolution_rate}%</div>
            <p className="text-xs text-muted-foreground">
              Avg {data.overview.avg_resolution_time}h to resolve
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">AI Performance</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.ai_performance.categorization_accuracy}%</div>
            <p className="text-xs text-muted-foreground">
              Categorization accuracy
            </p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="trends" className="space-y-4">
        <TabsList>
          <TabsTrigger value="trends">Ticket Trends</TabsTrigger>
          <TabsTrigger value="categories">Categories</TabsTrigger>
          <TabsTrigger value="priorities">Priorities</TabsTrigger>
          <TabsTrigger value="integrations">Integrations</TabsTrigger>
          <TabsTrigger value="ai">AI Performance</TabsTrigger>
        </TabsList>

        <TabsContent value="trends" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Ticket Volume Over Time</CardTitle>
              <CardDescription>
                Track ticket creation and resolution trends
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={data.ticket_trends}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="created" 
                    stroke={COLORS.primary} 
                    name="Created"
                    strokeWidth={2}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="resolved" 
                    stroke={COLORS.success} 
                    name="Resolved"
                    strokeWidth={2}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="open" 
                    stroke={COLORS.warning} 
                    name="Open"
                    strokeWidth={2}
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="categories" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>Category Distribution</CardTitle>
                <CardDescription>
                  Breakdown of tickets by category
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={data.category_distribution}
                      dataKey="count"
                      nameKey="category"
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      fill={COLORS.primary}
                    >
                      {data.category_distribution.map((entry, index) => (
                        <Cell 
                          key={`cell-${index}`} 
                          fill={Object.values(COLORS)[index % Object.values(COLORS).length]} 
                        />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Category Details</CardTitle>
                <CardDescription>
                  Detailed breakdown with percentages
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {data.category_distribution.map((category, index) => (
                    <div key={category.category} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div 
                          className="w-3 h-3 rounded-full" 
                          style={{ 
                            backgroundColor: Object.values(COLORS)[index % Object.values(COLORS).length] 
                          }}
                        />
                        <span className="font-medium capitalize">{category.category}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-muted-foreground">{category.count} tickets</span>
                        <Badge variant="outline">{category.percentage}%</Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="priorities" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Priority Breakdown</CardTitle>
              <CardDescription>
                Ticket distribution and resolution times by priority
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={data.priority_breakdown}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="priority" />
                  <YAxis yAxisId="left" />
                  <YAxis yAxisId="right" orientation="right" />
                  <Tooltip />
                  <Legend />
                  <Bar 
                    yAxisId="left"
                    dataKey="count" 
                    fill={COLORS.primary} 
                    name="Ticket Count"
                  />
                  <Bar 
                    yAxisId="right"
                    dataKey="avg_resolution_hours" 
                    fill={COLORS.warning} 
                    name="Avg Resolution (hours)"
                  />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="integrations" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Integration Usage</CardTitle>
              <CardDescription>
                Third-party integration performance and usage
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {data.integration_usage.map((integration) => (
                  <div key={integration.integration} className="flex items-center justify-between p-3 border rounded">
                    <div>
                      <h4 className="font-medium capitalize">{integration.integration}</h4>
                      <p className="text-sm text-muted-foreground">
                        {integration.tickets_created} tickets created
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge 
                        variant={integration.success_rate > 95 ? "default" : 
                               integration.success_rate > 80 ? "secondary" : "destructive"}
                      >
                        {integration.success_rate}% success
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="ai" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>AI Processing Stats</CardTitle>
                <CardDescription>
                  Performance metrics for AI-powered features
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Categorization Accuracy</span>
                  <Badge variant="default">{data.ai_performance.categorization_accuracy}%</Badge>
                </div>
                
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Avg Processing Time</span>
                  <Badge variant="secondary">{data.ai_performance.processing_time_avg}s</Badge>
                </div>
                
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Files Processed</span>
                  <Badge variant="outline">{data.ai_performance.files_processed}</Badge>
                </div>
                
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Transcription Success Rate</span>
                  <Badge 
                    variant={data.ai_performance.transcription_success_rate > 95 ? "default" : "secondary"}
                  >
                    {data.ai_performance.transcription_success_rate}%
                  </Badge>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>AI Recommendations</CardTitle>
                <CardDescription>
                  Suggested optimizations based on current performance
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {data.ai_performance.categorization_accuracy < 90 && (
                    <Alert>
                      <AlertTriangle className="h-4 w-4" />
                      <AlertDescription>
                        Consider updating categorization prompts to improve accuracy
                      </AlertDescription>
                    </Alert>
                  )}
                  
                  {data.ai_performance.processing_time_avg > 10 && (
                    <Alert>
                      <AlertTriangle className="h-4 w-4" />
                      <AlertDescription>
                        Processing time is high. Consider optimizing AI model parameters
                      </AlertDescription>
                    </Alert>
                  )}
                  
                  {data.ai_performance.transcription_success_rate < 85 && (
                    <Alert>
                      <AlertTriangle className="h-4 w-4" />
                      <AlertDescription>
                        Low transcription success rate. Check file quality requirements
                      </AlertDescription>
                    </Alert>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
```

## Integration Points

### Chrome Extension Messaging
```typescript
// src/services/chrome.ts - Chrome Extension Integration
interface ChromeMessage {
  type: string
  data: any
}

interface ChromeResponse {
  success: boolean
  data?: any
  error?: string
}

class ChromeExtensionService {
  private isExtensionContext = false

  constructor() {
    // Detect if running in Chrome extension context
    this.isExtensionContext = typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.id
  }

  async sendMessage(message: ChromeMessage): Promise<ChromeResponse> {
    if (!this.isExtensionContext) {
      throw new Error("Not running in Chrome extension context")
    }

    return new Promise((resolve) => {
      chrome.runtime.sendMessage(message, (response: ChromeResponse) => {
        if (chrome.runtime.lastError) {
          resolve({
            success: false,
            error: chrome.runtime.lastError.message
          })
        } else {
          resolve(response || { success: true })
        }
      })
    })
  }

  async captureTab(): Promise<string> {
    const response = await this.sendMessage({
      type: "CAPTURE_TAB",
      data: {}
    })
    
    if (!response.success) {
      throw new Error(response.error || "Failed to capture tab")
    }
    
    return response.data.dataUrl
  }

  async getPageContext(): Promise<{
    url: string
    title: string
    selectedText?: string
    cookies?: any[]
  }> {
    const response = await this.sendMessage({
      type: "GET_PAGE_CONTEXT", 
      data: {}
    })
    
    if (!response.success) {
      throw new Error(response.error || "Failed to get page context")
    }
    
    return response.data
  }

  onMessage(callback: (message: ChromeMessage) => void): () => void {
    if (!this.isExtensionContext) {
      return () => {}
    }

    const handler = (
      message: ChromeMessage,
      sender: chrome.runtime.MessageSender,
      sendResponse: (response: ChromeResponse) => void
    ) => {
      callback(message)
    }

    chrome.runtime.onMessage.addListener(handler)
    
    return () => {
      chrome.runtime.onMessage.removeListener(handler)
    }
  }
}

export const chromeService = new ChromeExtensionService()
```

### API Service Integration
```typescript
// src/services/api.ts - Main API Client
import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { useAuthStore } from '@/stores/authStore'

interface ApiResponse<T = any> {
  data: T
  message?: string
  status: number
}

class ApiService {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        const { token } = useAuthStore.getState()
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401) {
          const { logout } = useAuthStore.getState()
          logout()
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    )
  }

  async get<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response: AxiosResponse<T> = await this.client.get(url, config)
    return {
      data: response.data,
      status: response.status,
    }
  }

  async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response: AxiosResponse<T> = await this.client.post(url, data, config)
    return {
      data: response.data,
      status: response.status,
    }
  }

  async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response: AxiosResponse<T> = await this.client.put(url, data, config)
    return {
      data: response.data,
      status: response.status,
    }
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response: AxiosResponse<T> = await this.client.delete(url, config)
    return {
      data: response.data,
      status: response.status,
    }
  }

  async uploadFile(
    url: string,
    file: File,
    onProgress?: (progressEvent: ProgressEvent) => void
  ): Promise<ApiResponse> {
    const formData = new FormData()
    formData.append('file', file)

    return this.post(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: onProgress,
    })
  }
}

export const apiService = new ApiService()
```

## Validation Loop

### Level 1: TypeScript & Linting
```bash
# Run these FIRST - fix any errors before proceeding
npm run type-check           # TypeScript compilation check
npm run lint                 # ESLint with auto-fix
npm run format              # Prettier formatting
npm run build               # Production build validation

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit & Integration Tests
```typescript
// src/components/__tests__/TicketCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { TicketCard } from '../tickets/TicketCard'
import { Ticket } from '@/types/ticket'

const mockTicket: Ticket = {
  id: 1,
  title: "Test ticket",
  description: "Test description",
  status: "open",
  priority: "medium",
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
  category: "technical",
  attachments: [],
  comments_count: 0
}

describe('TicketCard', () => {
  const mockOnEdit = jest.fn()
  const mockOnView = jest.fn()

  beforeEach(() => {
    mockOnEdit.mockClear()
    mockOnView.mockClear()
  })

  it('renders ticket information correctly', () => {
    render(<TicketCard ticket={mockTicket} onEdit={mockOnEdit} onView={mockOnView} />)
    
    expect(screen.getByText('Test ticket')).toBeInTheDocument()
    expect(screen.getByText('Test description')).toBeInTheDocument()
    expect(screen.getByText('medium')).toBeInTheDocument()
    expect(screen.getByText('open')).toBeInTheDocument()
  })

  it('calls onView when card is clicked', () => {
    render(<TicketCard ticket={mockTicket} onEdit={mockOnEdit} onView={mockOnView} />)
    
    fireEvent.click(screen.getByRole('article') || screen.getByText('Test ticket'))
    expect(mockOnView).toHaveBeenCalledWith(mockTicket)
  })

  it('calls onEdit when edit button is clicked', () => {
    render(<TicketCard ticket={mockTicket} onEdit={mockOnEdit} onView={mockOnView} />)
    
    fireEvent.click(screen.getByText('Edit'))
    expect(mockOnEdit).toHaveBeenCalledWith(mockTicket)
    expect(mockOnView).not.toHaveBeenCalled() // Should not trigger view
  })
})

// src/hooks/__tests__/useWebSocket.test.tsx
import { renderHook, act } from '@testing-library/react'
import { useWebSocket } from '../useWebSocket'
import WS from 'jest-websocket-mock'

const TEST_URL = 'ws://localhost:8000/ws'

describe('useWebSocket', () => {
  let server: WS

  beforeEach(() => {
    server = new WS(TEST_URL)
  })

  afterEach(() => {
    WS.clean()
  })

  it('connects to WebSocket server', async () => {
    const { result } = renderHook(() => useWebSocket(TEST_URL))

    await server.connected
    expect(result.current.isConnected).toBe(true)
  })

  it('sends messages correctly', async () => {
    const { result } = renderHook(() => useWebSocket(TEST_URL))

    await server.connected

    const testMessage = { type: 'test', data: { message: 'hello' } }
    act(() => {
      result.current.sendMessage(testMessage)
    })

    await expect(server).toReceiveMessage(JSON.stringify(testMessage))
  })

  it('receives messages correctly', async () => {
    const mockOnMessage = jest.fn()
    const { result } = renderHook(() => 
      useWebSocket(TEST_URL, { onMessage: mockOnMessage })
    )

    await server.connected

    const testMessage = { type: 'notification', data: { title: 'Test' } }
    server.send(JSON.stringify(testMessage))

    expect(mockOnMessage).toHaveBeenCalledWith(testMessage)
    expect(result.current.lastMessage).toEqual(testMessage)
  })
})
```

### Level 3: E2E Tests
```typescript
// e2e/ticket-management.spec.ts
import { test, expect } from '@playwright/test'

test.describe('Ticket Management', () => {
  test.beforeEach(async ({ page }) => {
    // Mock API responses
    await page.route('/api/v1/tickets', async route => {
      await route.fulfill({
        json: {
          data: [
            {
              id: 1,
              title: 'Test ticket',
              description: 'Test description',
              status: 'open',
              priority: 'medium',
              created_at: '2024-01-01T00:00:00Z'
            }
          ],
          total: 1
        }
      })
    })

    await page.goto('/tickets')
  })

  test('displays ticket list', async ({ page }) => {
    await expect(page.locator('[data-testid="ticket-card"]')).toHaveCount(1)
    await expect(page.getByText('Test ticket')).toBeVisible()
    await expect(page.getByText('Test description')).toBeVisible()
  })

  test('opens ticket creation modal', async ({ page }) => {
    await page.click('[data-testid="create-ticket-button"]')
    await expect(page.getByRole('dialog')).toBeVisible()
    await expect(page.getByText('Create New Ticket')).toBeVisible()
  })

  test('creates new ticket with file upload', async ({ page }) => {
    await page.click('[data-testid="create-ticket-button"]')
    
    // Fill form
    await page.fill('[data-testid="ticket-title"]', 'New test ticket')
    await page.fill('[data-testid="ticket-description"]', 'New ticket description')
    
    // Upload file
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles('test-files/sample.pdf')
    
    // Submit form
    await page.click('[data-testid="submit-ticket"]')
    
    // Verify success
    await expect(page.getByText('Ticket created successfully')).toBeVisible()
  })
})
```

### Level 4: Accessibility & Performance
```bash
# Accessibility testing
npm run test:a11y              # Automated accessibility testing
npm run lighthouse             # Performance and accessibility audit

# Performance testing
npm run build && npm run preview  # Test production build
npm run test:bundle-size          # Bundle size analysis
```

## Deployment Configuration

### Package.json
```json
{
  "name": "ai-support-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "type-check": "tsc --noEmit",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "lint:fix": "eslint . --ext ts,tsx --fix",
    "format": "prettier --write \"src/**/*.{ts,tsx,js,jsx,css,md}\"",
    "test": "jest",
    "test:watch": "jest --watch", 
    "test:coverage": "jest --coverage",
    "test:e2e": "playwright test",
    "test:a11y": "jest --testMatch='**/*.a11y.test.{ts,tsx}'",
    "lighthouse": "lighthouse http://localhost:4173 --output-path=./lighthouse-report.html",
    "test:bundle-size": "bundlesize"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.15.0",
    "react-hook-form": "^7.45.0",
    "react-query": "@tanstack/react-query@^4.32.0",
    "@hookform/resolvers": "^3.3.0",
    "zod": "^3.22.0",
    "zustand": "^4.4.0",
    "axios": "^1.5.0",
    "date-fns": "^2.30.0",
    "recharts": "^2.7.0",
    "react-dropzone": "^14.2.3",
    "sonner": "^1.0.0",
    "lucide-react": "^0.263.0",
    "@radix-ui/react-slot": "^1.0.2",
    "@radix-ui/react-popover": "^1.0.6",
    "@radix-ui/react-dialog": "^1.0.4",
    "@radix-ui/react-select": "^1.2.2",
    "@radix-ui/react-switch": "^1.0.3",
    "@radix-ui/react-tabs": "^1.0.4",
    "@radix-ui/react-scroll-area": "^1.0.4",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.0.0",
    "tailwind-merge": "^1.14.0",
    "tailwindcss-animate": "^1.0.7"
  },
  "devDependencies": {
    "@types/react": "^18.2.21",
    "@types/react-dom": "^18.2.7",
    "@types/node": "^20.5.0",
    "@vitejs/plugin-react": "^4.0.4",
    "vite": "^4.4.9",
    "typescript": "^5.2.2",
    "tailwindcss": "^3.3.3",
    "autoprefixer": "^10.4.15",
    "postcss": "^8.4.29",
    "@typescript-eslint/eslint-plugin": "^6.5.0", 
    "@typescript-eslint/parser": "^6.5.0",
    "eslint": "^8.48.0",
    "eslint-plugin-react": "^7.33.2",
    "eslint-plugin-react-hooks": "^4.6.0",
    "eslint-plugin-jsx-a11y": "^6.7.1",
    "prettier": "^3.0.3",
    "jest": "^29.6.4",
    "@testing-library/react": "^13.4.0",
    "@testing-library/jest-dom": "^6.1.3",
    "@testing-library/user-event": "^14.4.3",
    "jest-environment-jsdom": "^29.6.4",
    "jest-websocket-mock": "^2.4.0",
    "@playwright/test": "^1.37.1",
    "bundlesize": "^0.18.1",
    "@axe-core/playwright": "^4.7.3"
  }
}
```

This comprehensive frontend PRP document provides a complete implementation plan for a modern React application that integrates with the AI Ticket Creator backend API, including real-time features, file handling, AI configuration management, and analytics dashboards.