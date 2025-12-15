import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { useToast } from "@/hooks/use-toast";
import { Package, Loader2 } from "lucide-react";

export default function Login() {
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await login(name, password, isAdmin);
      toast({
        title: "Welcome back!",
        description: `Logged in as ${name}`,
      });
      navigate("/");
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Authentication failed",
        description: error instanceof Error ? error.message : "Invalid credentials",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1 text-center">
          <div 
            className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-primary text-primary-foreground"
            aria-hidden="true"
          >
            <Package className="h-6 w-6" />
          </div>
          <CardTitle className="text-2xl font-bold" id="login-title">Model Registry</CardTitle>
          <CardDescription id="login-description">
            Sign in to access the Trustworthy Model Registry
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form 
            onSubmit={handleSubmit} 
            className="space-y-4"
            aria-labelledby="login-title"
            aria-describedby="login-description"
          >
            <div className="space-y-2">
              <Label htmlFor="name">
                Username <span className="text-destructive" aria-hidden="true">*</span>
                <span className="sr-only">(required)</span>
              </Label>
              <Input
                id="name"
                type="text"
                placeholder="Enter your username"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                autoComplete="username"
                aria-required="true"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">
                Password <span className="text-destructive" aria-hidden="true">*</span>
                <span className="sr-only">(required)</span>
              </Label>
              <Input
                id="password"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                aria-required="true"
              />
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox
                id="isAdmin"
                checked={isAdmin}
                onCheckedChange={(checked) => setIsAdmin(checked === true)}
                aria-describedby="admin-description"
              />
              <Label htmlFor="isAdmin" className="text-sm font-normal">
                Login as administrator
              </Label>
            </div>
            <p id="admin-description" className="sr-only">
              Check this option if you have administrator privileges
            </p>
            <Button 
              type="submit" 
              className="w-full" 
              disabled={isLoading}
              aria-describedby={isLoading ? "loading-status" : undefined}
            >
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />}
              {isLoading ? "Signing in..." : "Sign In"}
            </Button>
            {isLoading && (
              <p id="loading-status" className="sr-only" role="status" aria-live="polite">
                Signing in, please wait...
              </p>
            )}
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
