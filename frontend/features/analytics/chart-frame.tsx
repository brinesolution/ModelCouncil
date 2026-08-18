import type { ReactNode } from "react";

import { PanelDetails } from "@/components/industrial/panel-details";

interface ChartFrameProps {
  number: string;
  title: string;
  description: string;
  children: ReactNode;
  footer?: ReactNode;
}

export function ChartFrame({ number, title, description, children, footer }: ChartFrameProps) {
  return (
    <article className="analyticsCard">
      <PanelDetails vents={false} />
      <header className="analyticsCardHeader">
        <span className="chartIndex">{number}</span>
        <div>
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
      </header>
      <div className="analyticsChartBody">{children}</div>
      {footer ? <footer className="analyticsCardFooter">{footer}</footer> : null}
    </article>
  );
}
