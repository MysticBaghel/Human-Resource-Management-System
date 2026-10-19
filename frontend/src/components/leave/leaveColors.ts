/** A stable colour per leave type, used by the calendar dots and chips. */

const PALETTE = [
  { dot: "bg-emerald-500", chip: "bg-emerald-600 text-white" },
  { dot: "bg-sky-500", chip: "bg-sky-600 text-white" },
  { dot: "bg-violet-500", chip: "bg-violet-600 text-white" },
  { dot: "bg-amber-500", chip: "bg-amber-600 text-white" },
  { dot: "bg-rose-500", chip: "bg-rose-600 text-white" },
  { dot: "bg-teal-500", chip: "bg-teal-600 text-white" },
  { dot: "bg-indigo-500", chip: "bg-indigo-600 text-white" },
  { dot: "bg-fuchsia-500", chip: "bg-fuchsia-600 text-white" },
];

export function leaveDotClass(leaveTypeId: number): string {
  return PALETTE[Math.abs(leaveTypeId) % PALETTE.length].dot;
}

export function leaveChipClass(leaveTypeId: number): string {
  return PALETTE[Math.abs(leaveTypeId) % PALETTE.length].chip;
}
