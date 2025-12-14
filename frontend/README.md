# Model Registry MVP

A clean, professional frontend for managing AI models, datasets, and code artifacts.

## Project Info

**URL**: https://lovable.dev/projects/bcfc21ae-f966-4492-a56c-88da87686b69

## Features

- **Browse**: Paginated artifact listing with type filtering
- **Upload**: Upload new artifacts (models, datasets, code) as .zip files
- **Search**: Regex-based search across artifacts
- **Responsive Design**: Modern UI with accessible components

## Tech Stack

- React + TypeScript + Vite
- TanStack Query for data fetching
- Tailwind CSS + shadcn/ui components
- React Router for navigation

## Frontend Configuration

### Setting the API Base URL

The frontend communicates with a remote backend. Configure the API endpoint using an environment variable:

1. Copy `.env.example` to `.env.local`:
   ```bash
   cp .env.example .env.local
   ```

2. Set your backend URL in `.env.local`:
   ```
   VITE_API_BASE=https://your-backend-host:port
   ```

3. For local development, use:
   ```
   VITE_API_BASE=http://localhost:8000
   ```

**Important**: Never commit `.env.local` with real credentials. The `.env.example` file is for documentation only.

## API Endpoints Used

The frontend connects to the following backend endpoints:

### Upload
- `POST /artifact/{type}` - Upload new artifact (multipart/form-data)
  - Parameters: type (model|dataset|code)
  - Body: name, version, description, file

### Browse (with pagination)
- `POST /artifacts` - List artifacts with offset-based pagination
  - Headers: `offset: <number>` (current offset)
  - Query params: `limit` (page size), `type` (filter)
  - Response headers: `x-next-offset` (next page offset)

### Search
- `GET /artifact/by-regex` - Regex search
  - Query params: `pattern` (regex), `type` (filter), `limit`
  - Headers: `offset: <number>` for pagination

### Details (future)
- `GET /artifact/{id}` - Get artifact details
- `DELETE /artifact/{id}` - Delete artifact
- `PATCH /artifact/{id}` - Update artifact metadata

### Authentication (placeholder)
- `POST /auth/token` - Create auth token (not yet implemented in UI)

## Pagination Protocol

This app uses **offset-header pagination**:

1. Client sends current offset via `offset` header
2. Server returns items and the next offset in `x-next-offset` response header
3. Client maintains an offset history stack for "Previous" navigation
4. "Next" button is disabled when fewer than `limit` items are returned

## CORS Requirements

The backend must enable CORS for the frontend origin:

```python
# Backend CORS config
origins = ["https://your-frontend.example", "http://localhost:5173"]
allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
allow_headers = ["Content-Type", "offset", "Authorization"]
```

## Development

```bash
# Install dependencies
npm install

# Run dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Known Limitations (Milestone 2.4)

- **No authentication yet**: Auth endpoints exist but UI doesn't require login
- **Read-only details page**: Edit/Delete buttons are placeholders
- **Basic error handling**: More granular error states coming in future milestones
- **Mock data in dev**: Use `.env.local` to point to real backend when available

## Project Structure

```
src/
├── api/
│   ├── config.ts              # API client configuration
│   └── generated/             # OpenAPI generated client
│       ├── client.ts          # OpenAPI config
│       ├── services/          # Service methods
│       └── core/              # Request utilities
├── components/
│   ├── Navigation.tsx         # Top nav bar
│   ├── ArtifactCard.tsx       # Artifact display card
│   └── ui/                    # shadcn components
├── pages/
│   ├── BrowsePage.tsx         # Main listing (/)
│   ├── UploadPage.tsx         # Upload form (/upload)
│   ├── SearchPage.tsx         # Regex search (/search)
│   └── ArtifactDetails.tsx    # Details view (placeholder)
└── App.tsx                    # Router setup
```

## Next Steps (Post-Milestone 2.4)

- [ ] Add authentication (login/register)
- [ ] Implement artifact editing
- [ ] Add delete confirmation dialog
- [ ] Enhance error messages with retry logic
- [ ] Add artifact cost estimation display
- [ ] Implement file preview/download
- [ ] Add unit and e2e tests

---

## How can I edit this code?

There are several ways of editing your application.

**Use Lovable**

Simply visit the [Lovable Project](https://lovable.dev/projects/bcfc21ae-f966-4492-a56c-88da87686b69) and start prompting.

Changes made via Lovable will be committed automatically to this repo.

**Use your preferred IDE**

If you want to work locally using your own IDE, you can clone this repo and push changes. Pushed changes will also be reflected in Lovable.

The only requirement is having Node.js & npm installed - [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating)

Follow these steps:

```sh
# Step 1: Clone the repository using the project's Git URL.
git clone <YOUR_GIT_URL>

# Step 2: Navigate to the project directory.
cd <YOUR_PROJECT_NAME>

# Step 3: Install the necessary dependencies.
npm i

# Step 4: Start the development server with auto-reloading and an instant preview.
npm run dev
```

**Edit a file directly in GitHub**

- Navigate to the desired file(s).
- Click the "Edit" button (pencil icon) at the top right of the file view.
- Make your changes and commit the changes.

**Use GitHub Codespaces**

- Navigate to the main page of your repository.
- Click on the "Code" button (green button) near the top right.
- Select the "Codespaces" tab.
- Click on "New codespace" to launch a new Codespace environment.
- Edit files directly within the Codespace and commit and push your changes once you're done.

## What technologies are used for this project?

This project is built with:

- Vite
- TypeScript
- React
- shadcn-ui
- Tailwind CSS

## How can I deploy this project?

Simply open [Lovable](https://lovable.dev/projects/bcfc21ae-f966-4492-a56c-88da87686b69) and click on Share -> Publish.

## Can I connect a custom domain to my Lovable project?

Yes, you can!

To connect a domain, navigate to Project > Settings > Domains and click Connect Domain.

Read more here: [Setting up a custom domain](https://docs.lovable.dev/features/custom-domain#custom-domain)
