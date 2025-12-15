import { useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/use-toast";
import { Users, UserPlus, Shield, Loader2 } from "lucide-react";

export default function AdminUsers() {
  const { user } = useAuth();
  const { toast } = useToast();
  
  const [newUserName, setNewUserName] = useState("");
  const [newUserPassword, setNewUserPassword] = useState("");
  const [newUserIsAdmin, setNewUserIsAdmin] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!newUserName || !newUserPassword) {
      toast({
        variant: "destructive",
        title: "Missing fields",
        description: "Please fill in all required fields",
      });
      return;
    }

    setIsCreating(true);
    
    // Note: The API spec doesn't have a user creation endpoint
    // This is a placeholder for when such an endpoint is available
    setTimeout(() => {
      toast({
        title: "User creation not available",
        description: "User creation API endpoint is not implemented in the backend",
      });
      setIsCreating(false);
    }, 1000);
  };

  if (!user?.isAdmin) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <Shield className="h-12 w-12 text-muted-foreground/50" />
        <h2 className="mt-4 text-lg font-semibold">Access Denied</h2>
        <p className="text-sm text-muted-foreground">
          You need administrator privileges to access this page
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">User Management</h1>
        <p className="text-muted-foreground">
          Manage registry users and permissions
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserPlus className="h-5 w-5" />
              Create New User
            </CardTitle>
            <CardDescription>Add a new user to the registry</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreateUser} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="newUserName">Username</Label>
                <Input
                  id="newUserName"
                  placeholder="Enter username"
                  value={newUserName}
                  onChange={(e) => setNewUserName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="newUserPassword">Password</Label>
                <Input
                  id="newUserPassword"
                  type="password"
                  placeholder="Enter password"
                  value={newUserPassword}
                  onChange={(e) => setNewUserPassword(e.target.value)}
                />
              </div>
              <div className="flex items-center justify-between rounded-lg border p-4">
                <div className="space-y-0.5">
                  <Label htmlFor="newUserIsAdmin">Administrator</Label>
                  <p className="text-xs text-muted-foreground">
                    Grant admin privileges
                  </p>
                </div>
                <Switch
                  id="newUserIsAdmin"
                  checked={newUserIsAdmin}
                  onCheckedChange={setNewUserIsAdmin}
                />
              </div>
              <Button type="submit" className="w-full" disabled={isCreating}>
                {isCreating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Create User
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Current Session
            </CardTitle>
            <CardDescription>Your current user information</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-lg border p-4">
              <p className="text-sm font-medium">Username</p>
              <p className="text-lg">{user.name}</p>
            </div>
            <div className="rounded-lg border p-4">
              <p className="text-sm font-medium">Role</p>
              <p className="text-lg">{user.isAdmin ? "Administrator" : "User"}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>API Note</CardTitle>
          <CardDescription>About user management</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            The current API specification does not include endpoints for listing or managing users.
            User creation would need to be implemented in the backend to fully support this feature.
            Currently, users are authenticated via the /authenticate endpoint.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
