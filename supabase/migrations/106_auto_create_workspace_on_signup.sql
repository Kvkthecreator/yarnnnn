-- Migration 106: Auto-create workspace on user signup
--
-- New users had no workspace row, causing 500 errors on subscription/system
-- status endpoints. This trigger ensures every auth.users INSERT gets a
-- default workspace immediately.

-- 1. Function: create default workspace for new user
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.workspaces (name, owner_id)
  VALUES ('My Workspace', NEW.id)
  ON CONFLICT DO NOTHING;
  RETURN NEW;
END;
$$;

-- 2. Trigger: fire after auth.users insert
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

-- 3. Backfill: create workspace for any existing users who lack one
INSERT INTO public.workspaces (name, owner_id)
SELECT 'My Workspace', u.id
FROM auth.users u
LEFT JOIN public.workspaces w ON w.owner_id = u.id
WHERE w.id IS NULL;
