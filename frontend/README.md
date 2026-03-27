# Bharatiyam AI Assistant - Frontend

This is the React frontend for the Bharatiyam AI Assistant application.

## Prerequisites

- Node.js (v14 or later)
- npm (v6 or later)

## Setup Instructions

1. **Install Dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Start the Development Server**
   ```bash
   npm start
   ```
   This will start the React development server at http://localhost:3000

3. **Build for Production**
   ```bash
   npm run build
   ```
   This will create a `build` folder with optimized production build.

## Connecting to the Backend

The frontend is configured to proxy API requests to `http://localhost:8000` by default (see `proxy` in `package.json`). Make sure your FastAPI backend is running on that port.

## Environment Variables

Create a `.env` file in the `frontend` directory with the following variables:

```
REACT_APP_API_URL=http://localhost:8000
```

## Available Scripts

- `npm start`: Start the development server
- `npm test`: Run tests
- `npm run build`: Create a production build
- `npm run eject`: Eject from create-react-app (advanced)

## Project Structure

- `src/` - Source files
  - `App.js` - Main application component
  - `App.css` - Styles for the application
  - `index.js` - Application entry point
  - `index.css` - Global styles

## License

This project is licensed under the MIT License.
