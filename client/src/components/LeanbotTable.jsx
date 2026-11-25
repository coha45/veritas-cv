import { useState } from "react";
import Zone from "../Zone";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";

const columns = [
  { header: "ID", accessorKey: "id" },
  { header: "License Plate", accessorKey: "license_plate" },
  { 
    header: "Zone", 
    accessorKey: "current_zone",
    cell :  ({ getValue }) =>  {
      console.log("Current Zone: " + getValue)
      return getValue()
      /*
      const nz = new Zone(...getValue)
      return nz.tableDisplay()*/ 
    }
  },
  {
    header: "Speed (cm/s)",
    accessorKey: "speed",
    cell: ({ getValue }) => Number(getValue()).toFixed(1),
  },
  {
    header: "Angle (deg)",
    accessorKey: "angle",
    cell: ({ getValue }) => `${Number(getValue()).toFixed(1)}°`,
  },
  {
    header : "Violations",
    accessorKey : "violations",
    cell : ({ getValue }) => {
      console.log("Violations:", getValue)
      return getValue
    }
  }
];

export default function VehicleTable({ data }) {
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className="table-container overflow-x-scroll w-full">
      <table className="table w-full">
        <thead>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <th key={header.id}>
                  {flexRender(
                    header.column.columnDef.header,
                    header.getContext()
                  )}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id}>
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id}>
                  {flexRender(
                    cell.column.columnDef.cell,
                    cell.getContext()
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
