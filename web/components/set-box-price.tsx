import { formatKRW } from '@/lib/data';
import { formatYen } from '@/lib/set-msrp';
import { RegionLabel } from '@/components/ui';

type Props = {
  region: 'KR' | 'JP';
  marketPrice: number;
  msrpBox: number;
  msrpPack: number;
  boxLabel?: string;
};

export const SetBoxPriceRows = ({
  region,
  marketPrice,
  msrpBox,
  msrpPack,
  boxLabel = '박스',
}: Props) => {
  const formatPrice = region === 'KR' ? formatKRW : formatYen;
  const hasMarket = marketPrice > 0;

  return (
    <div className="flex justify-between items-start bg-slate-50 dark:bg-slate-950 p-3 rounded-lg border border-slate-100 dark:border-slate-800 gap-3">
      <RegionLabel region={region} suffix={` ${boxLabel}`} className="text-slate-600 dark:text-slate-400 shrink-0" />
      <div className="text-right min-w-0">
        {hasMarket ? (
          <>
            <div className="text-lg md:text-xl font-bold text-slate-900 dark:text-white leading-tight">
              {formatPrice(marketPrice)}
            </div>
            <p className="text-xs text-amber-600 dark:text-amber-500 font-medium mt-0.5">거래 시세</p>
          </>
        ) : (
          <div className="text-sm font-medium text-slate-500 dark:text-slate-400">시세 미등록</div>
        )}
        <p className="text-[11px] text-slate-400 mt-1 leading-snug">
          발매가 {formatPrice(msrpBox)}
          <span className="mx-1">·</span>
          팩 {formatPrice(msrpPack)}
        </p>
      </div>
    </div>
  );
};
