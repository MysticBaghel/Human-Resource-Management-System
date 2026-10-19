/** Team types and TanStack Query hooks. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiGet, apiPatch, apiPost } from "@/api/client";
import type { Paginated } from "@/api/types";
import { toQueryString } from "@/lib/query";

export type Team = {
  id: number;
  name: string;
  lead: number | null;
  lead_name: string | null;
  member_count: number;
};

export type TeamInput = {
  name: string;
  lead?: number | null;
};

export const teamKeys = {
  all: ["teams"] as const,
  list: (search: string) => [...teamKeys.all, "list", search] as const,
};

export function useTeams(search = "") {
  return useQuery({
    queryKey: teamKeys.list(search),
    queryFn: () =>
      apiGet<Paginated<Team>>(
        `/teams/${toQueryString({ search, page_size: 100 })}`,
      ),
  });
}

export function useCreateTeam() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: TeamInput) => apiPost<Team>("/teams/", input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: teamKeys.all });
    },
  });
}

export function useUpdateTeam(id: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: TeamInput) => apiPatch<Team>(`/teams/${id}/`, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: teamKeys.all });
      // Employee rows show the team name, so they go stale too.
      void queryClient.invalidateQueries({ queryKey: ["employees"] });
    },
  });
}
