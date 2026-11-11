export function addressCandidates(payload) {
  if (!Array.isArray(payload)) return [];
  return payload.filter(item=>item.address && ['portal','callejero'].includes(item.type))
    .map(item=>({label:item.address,lat:Number(item.lat),lon:Number(item.lng),type:item.type}));
}
export function validOrigin(candidate) {
  return Number.isFinite(candidate?.lat) && Number.isFinite(candidate?.lon)
    && candidate.lat>35 && candidate.lat<44.5 && candidate.lon>-10 && candidate.lon<5;
}
