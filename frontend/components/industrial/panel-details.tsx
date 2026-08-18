interface PanelDetailsProps {
  vents?: boolean;
  screws?: boolean;
}

export function PanelDetails({ vents = true, screws = true }: PanelDetailsProps) {
  return (
    <>
      {screws ? (
        <span className="panelScrews" aria-hidden="true">
          <i />
          <i />
          <i />
          <i />
        </span>
      ) : null}
      {vents ? (
        <span className="ventBank" aria-hidden="true">
          <i />
          <i />
          <i />
        </span>
      ) : null}
    </>
  );
}
