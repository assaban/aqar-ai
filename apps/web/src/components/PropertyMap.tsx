"use client";

import { useEffect, useRef } from "react";
import type { Property } from "@/lib/api";
import { formatPrice, PROPERTY_TYPE_LABELS } from "@/lib/utils";

interface PropertyMapProps {
  properties: Property[];
  center?: [number, number];
  zoom?: number;
  className?: string;
}

export default function PropertyMap({
  properties,
  center = [35.7595, -5.8340],
  zoom = 12,
  className = "h-[400px] w-full",
}: PropertyMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!mapRef.current || typeof window === "undefined") return;

    // Dynamic import of leaflet (client-only)
    import("leaflet").then((L) => {
      // Clean up existing map
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
      }

      const map = L.map(mapRef.current!, {
        center,
        zoom,
        zoomControl: true,
        scrollWheelZoom: true,
      });

      // OpenStreetMap tiles
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap contributors",
        maxZoom: 19,
      }).addTo(map);

      // Custom marker icon
      const markerIcon = L.divIcon({
        html: `<div style="
          background: #E8871E;
          width: 28px;
          height: 28px;
          border-radius: 50% 50% 50% 0;
          transform: rotate(-45deg);
          border: 3px solid white;
          box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        "></div>`,
        iconSize: [28, 28],
        iconAnchor: [14, 28],
        popupAnchor: [0, -28],
        className: "",
      });

      // Add property markers
      const markers: L.Marker[] = [];
      for (const prop of properties) {
        if (!prop.location) continue;

        const marker = L.marker(
          [prop.location.latitude, prop.location.longitude],
          { icon: markerIcon }
        );

        const typeLabel =
          PROPERTY_TYPE_LABELS[prop.property_type] || prop.property_type;

        marker.bindPopup(
          `<div style="font-family: sans-serif; min-width: 180px;">
            <p style="font-weight: 600; margin: 0 0 4px;">${prop.title_generated || "Propriété"}</p>
            <p style="color: #E8871E; font-weight: 700; margin: 0 0 4px;">
              ${formatPrice(prop.price)}
            </p>
            <p style="color: #78716C; font-size: 13px; margin: 0;">
              ${typeLabel} ${prop.area_sqm ? `· ${prop.area_sqm} m²` : ""} ${prop.rooms ? `· ${prop.rooms} pcs` : ""}
            </p>
            <a href="/property/${prop.id}" style="
              display: inline-block;
              margin-top: 8px;
              color: #0284C7;
              font-size: 13px;
              text-decoration: none;
            ">View details →</a>
          </div>`
        );

        marker.addTo(map);
        markers.push(marker);
      }

      // Fit bounds if we have markers
      if (markers.length > 0) {
        const group = L.featureGroup(markers);
        map.fitBounds(group.getBounds().pad(0.1));
      }

      mapInstanceRef.current = map;
    });

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [properties, center, zoom]);

  return <div ref={mapRef} className={`rounded-xl ${className}`} />;
}
