# DocuMind Frontend

Modern, professional React + TypeScript frontend for the DocuMind RAG system with advanced animations using Framer Motion.

## Features

- **Sharp, Modern UI**: No curved edges, professional developer-focused design
- **Advanced Animations**: Smooth Framer Motion animations on all interactions
- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile
- **Dark Theme**: Easy on the eyes with accent gradients
- **Free Icons**: Lucide-react SVG icons
- **Type-Safe**: Full TypeScript support
- **State Management**: Zustand for lightweight state management

## Tech Stack

- **React 18.3.1** - UI library
- **TypeScript** - Type safety
- **Vite** - Fast build tool
- **Framer Motion 11.3.28** - Advanced animations
- **React Router 6** - Client-side routing
- **Axios** - HTTP client
- **Lucide React** - SVG icons
- **React Dropzone** - File uploads
- **React Hot Toast** - Notifications
- **Zustand** - State management

## Getting Started

### Prerequisites

- Node.js 18+ (tested with v24.12.0)
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Environment Variables

Create a `.env` file:

```env
VITE_API_URL=http://localhost:8000
```

## Pages

### Home Page (`/`)
- Hero section with animated stats
- Feature cards with hover effects
- How it works section
- Call-to-action section

### Upload Page (`/upload`)
- Drag-and-drop file upload
- Multi-file support
- Progress tracking
- Real-time status updates

### Search Page (`/search`)
- AI-powered search interface
- Advanced filters (Top K, Hybrid Alpha)
- Real-time results with citations
- Score highlighting

### Documents Page (`/documents`)
- Document library view
- Grid/List view toggle
- Search functionality
- Delete management
- Statistics dashboard

## Design System

### Colors

```css
--bg-primary: #0A0E27;
--bg-secondary: #141B3D;
--accent-primary: #00D4FF;
--accent-secondary: #7C3AED;
--accent-tertiary: #EC4899;
```

### Typography

- Font: Inter (Google Fonts)
- Headers: 700-900 weight
- Body: 400-600 weight

### Animations

- Page transitions: Fade + slide
- Hover effects: Scale + translate
- Loading states: Spin + pulse
- Card animations: Stagger delays

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   └── Layout/
│   │       ├── Layout.tsx
│   │       ├── Layout.css
│   │       ├── Navbar.tsx
│   │       └── Navbar.css
│   ├── pages/
│   │   ├── HomePage.tsx/css
│   │   ├── UploadPage.tsx/css
│   │   ├── SearchPage.tsx/css
│   │   └── DocumentsPage.tsx/css
│   ├── services/
│   │   └── api.ts
│   ├── store/
│   │   └── useStore.ts
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── public/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

## API Integration

The frontend connects to the FastAPI backend at `http://localhost:8000`:

- `POST /api/documents/upload` - Upload documents
- `GET /api/documents` - List documents
- `DELETE /api/documents/{id}` - Delete document
- `POST /api/search` - Search documents
- `GET /api/health` - Health check

## Development

### Adding New Pages

1. Create component in `src/pages/`
2. Create matching CSS file
3. Add route to `App.tsx`
4. Add navigation link to `Navbar.tsx`

### Styling Guidelines

- **NO border-radius** - Keep all edges sharp
- Use CSS variables for colors
- Follow existing animation patterns
- Mobile-first responsive design
- Maintain consistent spacing scale

### Animation Guidelines

- Use Framer Motion for all animations
- Follow existing easing functions
- Stagger child animations for lists
- Add whileHover/whileTap to interactive elements

## Build & Deploy

```bash
# Build for production
npm run build

# Output: dist/
# Serve with any static hosting (Vercel, Netlify, etc.)
```

## Performance

- Vite HMR for instant updates
- Code splitting by route
- Optimized bundle size
- Lazy loading for images
- Efficient re-renders with React

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers

## License

MIT

## Author

Built with ❤️ for DocuMind RAG System
