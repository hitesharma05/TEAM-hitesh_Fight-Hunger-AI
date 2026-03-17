async function loadGoogleMaps() {
  try {
    const res = await fetch('/api/config/maps');
    const config = await res.json();
    
    if (config.key && config.key !== "" && !config.key.includes("YOUR_GOOGLE")) {
      const script = document.createElement('script');
      script.src = `https://maps.googleapis.com/maps/api/js?key=${config.key}&libraries=places&callback=initMap`;
      script.async = true;
      script.defer = true;
      document.head.appendChild(script);
    } else {
      console.warn("Google Maps API key not found or invalid.");
    }
  } catch (e) {
    console.error("Failed to fetch Google Maps API key:", e);
  }
}

window.initMap = function() {
  const defaultCenter = { lat: 18.9696, lng: 72.8196 }; // Mumbai Central
  
  // 1. Donation Form: Autocomplete
  const addressInput = document.getElementById('field-address');
  let donationMap = null;
  let donationMarker = null;

  if (addressInput) {
    const autocomplete = new google.maps.places.Autocomplete(addressInput);
    
    const mapContainer = document.getElementById('map-container');
    if (mapContainer) {
      mapContainer.innerHTML = ''; // Clear fallback UI
      donationMap = new google.maps.Map(mapContainer, {
        center: defaultCenter,
        zoom: 12,
        styles: getDarkMapStyle()
      });
      donationMarker = new google.maps.Marker({
        position: defaultCenter,
        map: donationMap,
        title: "Selected Location"
      });

      autocomplete.addListener('place_changed', () => {
        const place = autocomplete.getPlace();
        if (place.geometry && place.geometry.location) {
          donationMap.setCenter(place.geometry.location);
          donationMap.setZoom(15);
          donationMarker.setPosition(place.geometry.location);
        }
      });
    }
  }

  // 2. NGO Dashboard: Mini Map
  const dashMapEl = document.getElementById('dashboard-map');
  if (dashMapEl) {
    dashMapEl.innerHTML = ''; // Clear fallback UI
    const dashMap = new google.maps.Map(dashMapEl, {
      center: defaultCenter,
      zoom: 11,
      styles: getDarkMapStyle(),
      disableDefaultUI: true
    });
    loadNGOMarkers(dashMap);
  }

  // 3. NGO Dashboard: Full Map
  const dashFullMapEl = document.getElementById('dashboard-full-map');
  if (dashFullMapEl) {
    dashFullMapEl.innerHTML = ''; // Clear fallback UI
    const dashFullMap = new google.maps.Map(dashFullMapEl, {
      center: defaultCenter,
      zoom: 11,
      styles: getDarkMapStyle()
    });
    loadNGOMarkers(dashFullMap);
  }
};

async function loadNGOMarkers(map) {
  try {
    const res = await fetch('/api/ngos');
    const ngos = await res.json();
    
    ngos.forEach(ngo => {
      const marker = new google.maps.Marker({
        position: { lat: ngo.lat, lng: ngo.lng },
        map: map,
        title: ngo.name,
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          fillColor: ngo.status === 'online' ? '#2ecc71' : '#f39c12',
          fillOpacity: 0.9,
          scale: 8,
          strokeColor: '#fff',
          strokeWeight: 2
        }
      });
      
      const infoWindow = new google.maps.InfoWindow({
        content: `<div style="color:black;padding:5px"><b>${ngo.name}</b><br>${ngo.area}<br>Capacity: ${ngo.capacity} meals</div>`
      });
      
      marker.addListener('click', () => {
        infoWindow.open(map, marker);
      });
    });
  } catch (e) {
    console.error("Failed to load NGOs for map markers:", e);
  }
}

function getDarkMapStyle() {
  return [
    { elementType: "geometry", stylers: [{ color: "#242f3e" }] },
    { elementType: "labels.text.stroke", stylers: [{ color: "#242f3e" }] },
    { elementType: "labels.text.fill", stylers: [{ color: "#746855" }] },
    {
      featureType: "administrative.locality",
      elementType: "labels.text.fill",
      stylers: [{ color: "#d59563" }],
    },
    {
      featureType: "poi",
      elementType: "labels.text.fill",
      stylers: [{ color: "#d59563" }],
    },
    {
      featureType: "poi.park",
      elementType: "geometry",
      stylers: [{ color: "#263c3f" }],
    },
    {
      featureType: "poi.park",
      elementType: "labels.text.fill",
      stylers: [{ color: "#6b9a76" }],
    },
    {
      featureType: "road",
      elementType: "geometry",
      stylers: [{ color: "#38414e" }],
    },
    {
      featureType: "road",
      elementType: "geometry.stroke",
      stylers: [{ color: "#212a37" }],
    },
    {
      featureType: "road",
      elementType: "labels.text.fill",
      stylers: [{ color: "#9ca5b3" }],
    },
    {
      featureType: "road.highway",
      elementType: "geometry",
      stylers: [{ color: "#746855" }],
    },
    {
      featureType: "road.highway",
      elementType: "geometry.stroke",
      stylers: [{ color: "#1f2835" }],
    },
    {
      featureType: "road.highway",
      elementType: "labels.text.fill",
      stylers: [{ color: "#f3d19c" }],
    },
    {
      featureType: "transit",
      elementType: "geometry",
      stylers: [{ color: "#2f3948" }],
    },
    {
      featureType: "transit.station",
      elementType: "labels.text.fill",
      stylers: [{ color: "#d59563" }],
    },
    {
      featureType: "water",
      elementType: "geometry",
      stylers: [{ color: "#17263c" }],
    },
    {
      featureType: "water",
      elementType: "labels.text.fill",
      stylers: [{ color: "#515c6d" }],
    },
    {
      featureType: "water",
      elementType: "labels.text.stroke",
      stylers: [{ color: "#17263c" }],
    },
  ];
}

loadGoogleMaps();
